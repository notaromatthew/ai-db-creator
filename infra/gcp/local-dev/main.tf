# Sviluppo locale: progetto GCP con Vertex AI e una chiave del service account per docker-compose.local.vertex.yml.
# Stato LOCALE (ignorato da git). Separato dalla produzione (../ e ../bootstrap).
terraform {
  required_version = ">= 1.6"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
  }
}

variable "project_id" {
  type    = string
  default = "aidbcreator-research-2026"
}

variable "project_name" {
  type    = string
  default = "AI DB Creator Research"
}

variable "billing_account_id" {
  description = "ID dell'account di fatturazione (gcloud billing accounts list)"
  type        = string
}

variable "region" {
  type    = string
  default = "europe-west4"
}

variable "credentials_file" {
  description = "Dove scrivere la chiave JSON (percorso ignorato da git)"
  type        = string
  default     = "../../../.secrets/vertex-sa.json"
}

provider "google" {
  project               = var.project_id
  region                = var.region
  user_project_override = true
  billing_project       = var.project_id
}

resource "google_project" "this" {
  name            = var.project_name
  project_id      = var.project_id
  billing_account = var.billing_account_id
  deletion_policy = "PREVENT"
}

resource "google_project_service" "apis" {
  for_each                   = toset(["aiplatform.googleapis.com", "iam.googleapis.com", "cloudresourcemanager.googleapis.com", "serviceusage.googleapis.com"])
  project                    = google_project.this.project_id
  service                    = each.value
  disable_on_destroy         = false
  disable_dependent_services = false
}

resource "google_service_account" "runner" {
  project      = google_project.this.project_id
  account_id   = "aidb-runner"
  display_name = "AI DB Creator runner"
  depends_on   = [google_project_service.apis]
}

resource "google_project_iam_member" "runner_vertex" {
  project = google_project.this.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.runner.email}"
}

resource "google_service_account_key" "runner" {
  service_account_id = google_service_account.runner.name
}

resource "local_sensitive_file" "credentials" {
  content         = base64decode(google_service_account_key.runner.private_key)
  filename        = var.credentials_file
  file_permission = "0600"
}

import {
  to = google_project.this
  id = "projects/aidbcreator-research-2026"
}

import {
  to = google_service_account.runner
  id = "projects/aidbcreator-research-2026/serviceAccounts/aidb-runner@aidbcreator-research-2026.iam.gserviceaccount.com"
}

import {
  to = google_project_iam_member.runner_vertex
  id = "aidbcreator-research-2026 roles/aiplatform.user serviceAccount:aidb-runner@aidbcreator-research-2026.iam.gserviceaccount.com"
}

import {
  to = google_project_service.apis["aiplatform.googleapis.com"]
  id = "aidbcreator-research-2026/aiplatform.googleapis.com"
}
