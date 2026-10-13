resource "random_id" "suffix" {
  byte_length = 3
}

locals {
  project_id = "aidb-creator-${random_id.suffix.hex}"
  apis = [
    "aiplatform.googleapis.com",
    "iam.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "serviceusage.googleapis.com",
    "billingbudgets.googleapis.com",
    "secretmanager.googleapis.com",
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
  ]
}

resource "google_project" "this" {
  name            = var.project_name
  project_id      = local.project_id
  billing_account = var.billing_account_id
  deletion_policy = "PREVENT"
}

resource "google_project_service" "apis" {
  for_each                   = toset(local.apis)
  project                    = google_project.this.project_id
  service                    = each.value
  disable_on_destroy         = false
  disable_dependent_services = false
}

# Identita' con cui l'app chiama Vertex AI: solo il ruolo "aiplatform.user".
resource "google_service_account" "vertex_caller" {
  project      = google_project.this.project_id
  account_id   = "aidb-vertex-caller"
  display_name = "AI-DB-Creator, chiamate a Vertex AI"
  depends_on   = [google_project_service.apis]
}

resource "google_project_iam_member" "vertex_user" {
  project = google_project.this.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.vertex_caller.email}"
}

resource "google_service_account_key" "vertex_caller" {
  count              = var.create_service_account_key ? 1 : 0
  service_account_id = google_service_account.vertex_caller.name
}

# Avvisi di spesa al 50%, 90% e 100% della soglia mensile.
resource "google_billing_budget" "monthly" {
  billing_account = var.billing_account_id
  display_name    = "AI-DB-Creator, soglia mensile"

  budget_filter {
    projects = ["projects/${google_project.this.number}"]
  }

  amount {
    specified_amount {
      currency_code = "EUR"
      units         = tostring(var.monthly_budget_eur)
    }
  }

  threshold_rules { threshold_percent = 0.5 }
  threshold_rules { threshold_percent = 0.9 }
  threshold_rules { threshold_percent = 1.0 }

  depends_on = [google_project_service.apis]
}
