variable "label" {
  type = string
}

variable "acs_url" {
  type = string
}

variable "entity_id" {
  type = string
}

variable "assigned_group_ids" {
  type = list(string)
}

variable "authentication_policy_id" {
  type = string
}

variable "enterprise_attributes" {
  description = "SCIM enterprise extension attribute => Okta expression that fills it."
  type        = map(string)
  default = {
    department = "user.department"
    costCenter = "user.costCenter"
  }
}

variable "provisioning_enabled" {
  description = "Set true after SCIM provisioning is switched on for the app (console step for custom apps)."
  type        = bool
  default     = false
}

variable "push_group_ids" {
  description = "Okta groups pushed to the app as SCIM groups."
  type        = list(string)
  default     = []
}

variable "manage_connection" {
  description = "Manage the provisioning connection with okta_app_connection. Only for apps Okta supports there; custom SCIM apps are configured in the console."
  type        = bool
  default     = false
}

variable "scim_base_url" {
  type    = string
  default = ""

  validation {
    condition     = var.scim_base_url == "" || startswith(var.scim_base_url, "https://")
    error_message = "SCIM base URL must use https."
  }
}

variable "scim_token" {
  type      = string
  default   = ""
  sensitive = true
}
