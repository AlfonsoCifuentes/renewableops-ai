variable "subscription_id" {
  description = "Azure subscription used only when this reference stack is explicitly applied."
  type        = string
}

variable "location" {
  description = "Primary Azure region."
  type        = string
  default     = "westeurope"
}

variable "environment" {
  description = "Short deployment environment."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging or prod."
  }
}

variable "owner" {
  description = "Operational owner used in resource tags."
  type        = string
  default     = "renewableops"
}

variable "monthly_budget_eur" {
  description = "Monthly budget guardrail. Alerts do not prevent spend."
  type        = number
  default     = 25
}

variable "budget_contact_emails" {
  description = "Addresses that receive Azure budget notifications."
  type        = list(string)
  default     = []
}

variable "postgres_admin_password" {
  description = "PostgreSQL administrator password; inject from a secret store."
  type        = string
  sensitive   = true
}

variable "enable_paid_reference" {
  description = "Create billable PostgreSQL, Databricks, Event Hubs, ML and Container Apps resources."
  type        = bool
  default     = false
}

variable "allowed_deployer_object_ids" {
  description = "Entra object IDs granted Key Vault administration."
  type        = set(string)
  default     = []
}
