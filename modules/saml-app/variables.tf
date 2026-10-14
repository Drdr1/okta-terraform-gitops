variable "label" {
  type = string
}

variable "acs_url" {
  description = "Service provider Assertion Consumer Service URL."
  type        = string
}

variable "entity_id" {
  description = "Service provider entity ID (SAML audience)."
  type        = string
}

variable "attributes" {
  description = "Attribute statements: SAML attribute name => Okta expression."
  type        = map(string)
  default = {
    email     = "user.email"
    firstName = "user.firstName"
    lastName  = "user.lastName"
  }
}

variable "groups_attribute_regex" {
  description = "Send groups whose name matches this regex. null = no groups attribute."
  type        = string
  default     = null
}

variable "assigned_group_ids" {
  type = list(string)

  validation {
    condition     = length(var.assigned_group_ids) > 0
    error_message = "Assign at least one group."
  }
}

variable "authentication_policy_id" {
  type = string
}
