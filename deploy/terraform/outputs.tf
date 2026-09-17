output "container_app_fqdn" {
  value       = "https://${azurerm_container_app.backend.ingress[0].fqdn}/swagger-ui/index.html"
  description = "Public Swagger UI URL of Smart-Document-Chatbot"
}
