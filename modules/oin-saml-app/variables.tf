variable "catalog_name" {
  description = "OIN app name, e.g. amazon_aws. Find it with GET /api/v1/apps/{id} -> name on an app added once by hand in a sandbox."
  type        = string
}

variable "label" {
  type = string
}

variable "settings" {
  description = "App-specific settings (settings.app in the Apps API)."
  type        = any
  default     = {}
}

variable "assigned_groups" {
  description = "Groups to assign, each with the app-specific assignment profile (e.g. AWS role)."
  type = list(object({
    id      = string
    profile = any
  }))
}

variable "authentication_policy_id" {
  type = string
}
