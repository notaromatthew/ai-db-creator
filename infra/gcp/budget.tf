resource "google_monitoring_notification_channel" "email" {
  count        = var.budget_alert_email != "" ? 1 : 0
  project      = var.project_id
  display_name = "AI-DB-Creator, avvisi di spesa"
  type         = "email"
  labels = {
    email_address = var.budget_alert_email
  }
  depends_on = [google_project_service.apis]
}

# Avvisi al 50%, 90%, 100% e 120% della soglia mensile.
# Il budget AVVISA soltanto: il freno automatico e' daily_request_cap del gateway;
# lo spegnimento manuale e' ai_enabled=false (scripts/ops_gateway_off.sh). Vedi docs/ops/spegnimento-gateway.md
resource "google_billing_budget" "monthly" {
  billing_account = var.billing_account_id
  display_name    = "AI-DB-Creator, soglia mensile"

  budget_filter {
    projects = ["projects/${data.google_project.this.number}"]
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
  threshold_rules { threshold_percent = 1.2 }

  dynamic "all_updates_rule" {
    for_each = var.budget_alert_email != "" ? [1] : []
    content {
      monitoring_notification_channels = [google_monitoring_notification_channel.email[0].id]
      disable_default_iam_recipients   = false
    }
  }

  depends_on = [google_project_service.apis]
}
