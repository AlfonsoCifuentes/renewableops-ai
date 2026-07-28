output "resource_group_name" {
  description = "Resource group containing the reference architecture."
  value       = azurerm_resource_group.main.name
}

output "storage_account_name" {
  description = "Private ADLS Gen2 account."
  value       = azurerm_storage_account.lake.name
}

output "workload_identity_client_id" {
  description = "Managed identity client ID for workload federation."
  value       = azurerm_user_assigned_identity.workload.client_id
}

output "log_analytics_workspace_id" {
  description = "Central diagnostics workspace resource ID."
  value       = azurerm_log_analytics_workspace.main.id
}

output "databricks_workspace_url" {
  description = "Azure Databricks URL when the paid reference is enabled."
  value       = var.enable_paid_reference ? azurerm_databricks_workspace.main[0].workspace_url : null
}
