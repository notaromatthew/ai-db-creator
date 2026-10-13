output "project_id" {
  value = var.project_id
}

output "gateway_url" {
  description = "Valore di LLM_GATEWAY_URL in Coolify"
  value       = google_cloud_run_v2_service.gateway.uri
}

output "gateway_audience" {
  value = local.gateway_url
}

output "caller_service_account" {
  value = google_service_account.caller.email
}

output "artifact_registry_image_base" {
  description = "Prefisso per docker build/push del gateway"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.gateway.repository_id}/gateway"
}

output "caller_key_secret" {
  description = "Segreto Secret Manager con la chiave del chiamante (se create_caller_key = true)"
  value       = google_secret_manager_secret.caller_key.secret_id
}
