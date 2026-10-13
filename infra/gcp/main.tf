data "google_project" "this" {
  project_id = var.project_id
}

locals {
  apis = [
    "aiplatform.googleapis.com",
    "iam.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "serviceusage.googleapis.com",
    "billingbudgets.googleapis.com",
    "monitoring.googleapis.com",
    "secretmanager.googleapis.com",
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
  ]
  gateway_name = "aidb-gateway"
  # URL deterministico di Cloud Run (nome-numeroProgetto.regione.run.app): serve come audience OIDC.
  gateway_url = "https://${local.gateway_name}-${data.google_project.this.number}.${var.region}.run.app"
  image       = var.gateway_image != "" ? var.gateway_image : "us-docker.pkg.dev/cloudrun/container/hello"
}

resource "google_project_service" "apis" {
  for_each                   = toset(local.apis)
  project                    = var.project_id
  service                    = each.value
  disable_on_destroy         = false
  disable_dependent_services = false
}

# Registro delle immagini del gateway.
resource "google_artifact_registry_repository" "gateway" {
  project       = var.project_id
  location      = var.region
  repository_id = "aidb"
  format        = "DOCKER"
  description   = "Immagini del gateway AI-DB-Creator"
  depends_on    = [google_project_service.apis]
}

# Identita' del gateway: l'UNICA con accesso a Vertex (solo aiplatform.user).
resource "google_service_account" "gateway" {
  project      = var.project_id
  account_id   = "aidb-gateway"
  display_name = "AI-DB-Creator, gateway (chiama Vertex)"
  depends_on   = [google_project_service.apis]
}

resource "google_project_iam_member" "gateway_vertex" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.gateway.email}"
}

# Identita' del chiamante (l'app su Coolify): puo' solo invocare il gateway.
resource "google_service_account" "caller" {
  project      = var.project_id
  account_id   = "aidb-gateway-caller"
  display_name = "AI-DB-Creator, chiamante del gateway"
  depends_on   = [google_project_service.apis]
}

resource "google_cloud_run_v2_service" "gateway" {
  project             = var.project_id
  name                = local.gateway_name
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false # permette distruggi e ricrea (docs/ops/ricreazione.md)

  template {
    service_account = google_service_account.gateway.email
    timeout         = "130s"

    # max 1: il tetto giornaliero e' un contatore in memoria, quindi una sola istanza lo rende esatto.
    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    containers {
      image = local.image
      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
      env {
        name  = "GATEWAY_AUDIENCE"
        value = local.gateway_url
      }
      env {
        name  = "ALLOWED_CALLERS"
        value = google_service_account.caller.email
      }
      env {
        name  = "VERTEX_PROJECT"
        value = var.project_id
      }
      env {
        name  = "VERTEX_LOCATION"
        value = var.region
      }
      env {
        name  = "VERTEX_MODEL"
        value = var.vertex_model
      }
      env {
        name  = "MAX_OUTPUT_TOKENS"
        value = tostring(var.max_output_tokens)
      }
      env {
        name  = "AI_ENABLED"
        value = tostring(var.ai_enabled)
      }
      env {
        name  = "DAILY_REQUEST_CAP"
        value = tostring(var.daily_request_cap)
      }
    }
  }

  depends_on = [google_project_iam_member.gateway_vertex]
}

# Solo il chiamante puo' invocare il servizio (nessun allUsers).
resource "google_cloud_run_v2_service_iam_member" "caller_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.gateway.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.caller.email}"
}

# Segreto con la chiave del chiamante, da leggere e incollare in Coolify (GATEWAY_CALLER_CREDENTIALS_JSON).
resource "google_secret_manager_secret" "caller_key" {
  project   = var.project_id
  secret_id = "gateway-caller-key"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_service_account_key" "caller" {
  count              = var.create_caller_key ? 1 : 0
  service_account_id = google_service_account.caller.name
}

resource "google_secret_manager_secret_version" "caller_key" {
  count       = var.create_caller_key ? 1 : 0
  secret      = google_secret_manager_secret.caller_key.id
  secret_data = base64decode(google_service_account_key.caller[0].private_key)
}
