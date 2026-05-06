output "AZURE_FUNCTION_APP_NAME" {
  value = azurerm_function_app_flex_consumption.func.name
}

output "AZURE_FUNCTION_APP_HOSTNAME" {
  value = azurerm_function_app_flex_consumption.func.default_hostname
}

output "AZURE_KEY_VAULT_NAME" {
  value = azurerm_key_vault.kv.name
}

output "AZURE_KEY_VAULT_URL" {
  value = azurerm_key_vault.kv.vault_uri
}

output "AZURE_USER_ASSIGNED_IDENTITY_ID" {
  value = azurerm_user_assigned_identity.uami.id
}

output "AZURE_USER_ASSIGNED_IDENTITY_CLIENT_ID" {
  value = azurerm_user_assigned_identity.uami.client_id
}

output "AZURE_RESOURCE_GROUP" {
  value = data.azurerm_resource_group.rg.name
}

output "APPLICATIONINSIGHTS_CONNECTION_STRING" {
  value     = azurerm_application_insights.appi.connection_string
  sensitive = true
}

output "AZURE_RESOURCE_TOKEN" {
  value       = local.resource_token
  description = "Deterministic name suffix used for every resource. Pin this on subsequent runs to keep names stable."
}
