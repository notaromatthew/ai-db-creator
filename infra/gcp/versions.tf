terraform {
  required_version = ">= 1.6"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
  # Stato remoto nel bucket creato da bootstrap/. Il nome del bucket NON sta nel codice:
  #   terraform init -backend-config="bucket=<tfstate_bucket>"
  backend "gcs" {
    prefix = "aidb-creator/main"
  }
}

provider "google" {
  project               = var.project_id
  region                = var.region
  user_project_override = true
  billing_project       = var.project_id
}
