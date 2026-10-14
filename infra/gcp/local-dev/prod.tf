# Produzione a costo minimo: l'app su Coolify chiama Vertex direttamente, senza gateway.
# Identita' separata da quella locale (aidb-runner) e ruotabile; la chiave si crea solo con create_prod_key=true.
variable "create_prod_key" {
  description = "Crea la chiave JSON del service account di produzione e la scrive in prod_credentials_file (per Coolify)"
  type        = bool
  default     = false
}

variable "prod_credentials_file" {
  type    = string
  default = "../../../.secrets/vertex-prod-sa.json"
}

variable "monthly_budget_eur" {
  description = "Soglia mensile del budget (solo avvisi, non blocca la spesa)"
  type        = number
  default     = 5
}

variable "budget_alert_email" {
  description = "Email degli avvisi di budget"
  type        = string
  default     = ""
}

resource "google_service_account" "prod" {
  project      = google_project.this.project_id
  account_id   = "aidb-prod"
  display_name = "AI DB Creator produzione (Coolify)"
  depends_on   = [google_project_service.apis]
}

resource "google_project_iam_member" "prod_vertex" {
  project = google_project.this.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.prod.email}"
}

resource "google_service_account_key" "prod" {
  count              = var.create_prod_key ? 1 : 0
  service_account_id = google_service_account.prod.name
}

resource "local_sensitive_file" "prod_credentials" {
  count           = var.create_prod_key ? 1 : 0
  content         = base64decode(google_service_account_key.prod[0].private_key)
  filename        = var.prod_credentials_file
  file_permission = "0600"
}

resource "google_project_service" "budget_apis" {
  for_each                   = toset(["billingbudgets.googleapis.com", "monitoring.googleapis.com"])
  project                    = google_project.this.project_id
  service                    = each.value
  disable_on_destroy         = false
  disable_dependent_services = false
}

resource "google_monitoring_notification_channel" "email" {
  count        = var.budget_alert_email != "" ? 1 : 0
  project      = google_project.this.project_id
  display_name = "AI DB Creator, avvisi di spesa"
  type         = "email"
  labels       = { email_address = var.budget_alert_email }
  depends_on   = [google_project_service.budget_apis]
}

# Il budget AVVISA soltanto. I freni veri sono la quota Vertex (richieste al minuto, da impostare in GCP)
# e i tetti dell'app (DEFAULT_DAILY_AI_QUOTA, DAILY_AI_BUDGET_TOTAL).
resource "google_billing_budget" "monthly" {
  billing_account = var.billing_account_id
  display_name    = "AI DB Creator, soglia mensile"

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
  threshold_rules { threshold_percent = 1.5 }

  dynamic "all_updates_rule" {
    for_each = var.budget_alert_email != "" ? [1] : []
    content {
      monitoring_notification_channels = [google_monitoring_notification_channel.email[0].id]
      disable_default_iam_recipients   = false
    }
  }

  depends_on = [google_project_service.budget_apis]
}
