variable "label" {
  description = "App name shown to users."
  type        = string
}

variable "auth_server_name" {
  description = "Name of the custom authorization server."
  type        = string
}

variable "audience" {
  description = "aud claim of access tokens, usually the API base URL."
  type        = string
}

variable "custom_scopes" {
  description = "Custom scopes on the auth server: name => description."
  type        = map(string)
  default     = {}
}

variable "redirect_uris" {
  type = list(string)
}

variable "post_logout_redirect_uris" {
  type    = list(string)
  default = []
}

variable "assigned_group_ids" {
  description = "Groups assigned to the app and allowed by the token policy. Order sets assignment priority."
  type        = list(string)

  validation {
    condition     = length(var.assigned_group_ids) > 0
    error_message = "Assign at least one group. Apps with no assignments cannot be used."
  }
}

variable "groups_claim_prefix" {
  description = "Only groups whose name starts with this go into the groups claim."
  type        = string
  default     = ""
}

variable "authentication_policy_id" {
  description = "ID of an okta_app_signon_policy."
  type        = string
}
