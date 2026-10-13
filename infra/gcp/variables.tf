variable "billing_account_id" {
  description = "ID dell'account di fatturazione collegato a Davide (formato XXXXXX-XXXXXX-XXXXXX). Si legge con: gcloud billing accounts list"
  type        = string
}

variable "project_name" {
  description = "Nome leggibile del progetto"
  type        = string
  default     = "AI-DB-Creator"
}

variable "region" {
  description = "Regione UE a basso costo per Vertex AI e Cloud Run"
  type        = string
  default     = "europe-west4"
}

variable "monthly_budget_eur" {
  description = "Soglia mensile oltre la quale partono gli avvisi di spesa (non blocca la spesa)"
  type        = number
  default     = 20
}

variable "budget_alert_email" {
  description = "Email che riceve gli avvisi di spesa (se vuota usa solo i destinatari dell'account di fatturazione)"
  type        = string
  default     = ""
}

variable "create_service_account_key" {
  description = "Crea una chiave JSON per il service account da incollare in Coolify (VERTEX_CREDENTIALS_JSON). La chiave finisce nello stato locale."
  type        = bool
  default     = false
}
