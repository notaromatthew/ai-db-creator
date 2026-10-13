variable "project_id" {
  description = "ID del progetto creato da bootstrap/ (output project_id)"
  type        = string
}

variable "billing_account_id" {
  description = "ID dell'account di fatturazione (serve al budget). gcloud billing accounts list"
  type        = string
}

variable "region" {
  description = "Regione UE a basso costo per Vertex AI e Cloud Run"
  type        = string
  default     = "europe-west4"
}

variable "monthly_budget_eur" {
  description = "Soglia mensile del budget (avvisi; non blocca la spesa da sola)"
  type        = number
  default     = 20
}

variable "budget_alert_email" {
  description = "Email che riceve gli avvisi di budget (vuota = solo destinatari dell'account di fatturazione)"
  type        = string
  default     = ""
}

variable "ai_enabled" {
  description = "Interruttore del gateway: false = il gateway risponde 503 a ogni richiesta AI. Si cambia con scripts/ops_gateway_off.sh"
  type        = bool
  default     = true
}

variable "daily_request_cap" {
  description = "Tetto di richieste AI al giorno (UTC) accettate dal gateway"
  type        = number
  default     = 500
}

variable "gateway_image" {
  description = "Immagine del gateway in Artifact Registry. Vuota = immagine segnaposto di Google finche' non si pubblica la prima"
  type        = string
  default     = ""
}

variable "vertex_model" {
  description = "Modello Vertex fissato lato gateway"
  type        = string
  default     = "gemini-2.5-flash-lite"
}

variable "max_output_tokens" {
  description = "Token massimi in uscita, fissati lato gateway"
  type        = number
  default     = 2048
}

variable "create_caller_key" {
  description = "Crea la chiave JSON del service account chiamante e la salva in Secret Manager (per Coolify). La chiave finisce anche nello stato remoto."
  type        = bool
  default     = false
}
