variable "name" {
  type = string
}

variable "issuer" {
  description = "Entity ID of the external IdP."
  type        = string
}

variable "sso_url" {
  description = "SSO (HTTP-POST) URL of the external IdP."
  type        = string
}

variable "signing_cert" {
  description = "IdP signing certificate, base64 DER (PEM body without header lines)."
  type        = string
}

variable "jit_group_ids" {
  description = "Groups every JIT user is added to."
  type        = list(string)
}

variable "email_domains" {
  description = "Users with these email domains are sent to this IdP."
  type        = list(string)
}

variable "idp_is_profile_master" {
  description = "true = the IdP owns profile attributes on every sign-in."
  type        = bool
  default     = true
}

variable "routing_priority" {
  type    = number
  default = 1
}
