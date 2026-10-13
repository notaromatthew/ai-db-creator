# Bootstrap: crea il progetto dedicato e il bucket (versionato) che ospita lo stato remoto
# del Terraform principale. Questa cartella usa STATO LOCALE (ignorato da git, da custodire fuori dal repo).
terraform {
  required_version = ">= 1.6"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

variable "billing_account_id" {
  description = "ID dell'account di fatturazione (gcloud billing accounts list)"
  type        = string
}

variable "project_name" {
  type    = string
  default = "AI-DB-Creator"
}

variable "region" {
  type    = string
  default = "europe-west4"
}

resource "random_id" "suffix" {
  byte_length = 3
}

locals {
  project_id  = "aidb-creator-${random_id.suffix.hex}"
  bucket_name = "${local.project_id}-tfstate"
}

provider "google" {
  region = var.region
}

resource "google_project" "this" {
  name            = var.project_name
  project_id      = local.project_id
  billing_account = var.billing_account_id
  deletion_policy = "PREVENT"
  # niente rete "default" aperta: serve solo Cloud Run + Vertex
  auto_create_network = false
}

resource "google_project_service" "bootstrap" {
  for_each                   = toset(["storage.googleapis.com", "serviceusage.googleapis.com", "cloudresourcemanager.googleapis.com"])
  project                    = google_project.this.project_id
  service                    = each.value
  disable_on_destroy         = false
  disable_dependent_services = false
}

resource "google_storage_bucket" "tfstate" {
  project                     = google_project.this.project_id
  name                        = local.bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      num_newer_versions = 20
      with_state         = "ARCHIVED"
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.bootstrap]
}

output "project_id" {
  value = google_project.this.project_id
}

output "tfstate_bucket" {
  value = google_storage_bucket.tfstate.name
}

output "init_command" {
  value = "cd infra/gcp && terraform init -backend-config=\"bucket=${google_storage_bucket.tfstate.name}\""
}
