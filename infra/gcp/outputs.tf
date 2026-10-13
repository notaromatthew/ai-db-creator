output "project_id" {
  value = google_project.this.project_id
}

output "vertex_location" {
  value = var.region
}

output "service_account_email" {
  value = google_service_account.vertex_caller.email
}

# Da incollare in Coolify come VERTEX_CREDENTIALS_JSON (solo se create_service_account_key = true)
output "service_account_key_json" {
  value     = var.create_service_account_key ? base64decode(google_service_account_key.vertex_caller[0].private_key) : ""
  sensitive = true
}
