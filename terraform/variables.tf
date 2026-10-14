variable "environment" {
  description = "Short name of the Okta org this state manages (nonprod, prod)."
  type        = string
  default     = "nonprod"
}

variable "office_cidrs" {
  description = "Egress IP ranges of company offices and VPN, in CIDR form."
  type        = list(string)
  default     = ["198.51.100.0/24"] # RFC 5737 documentation range
}

variable "blocked_cidrs" {
  description = "IP ranges denied before authentication."
  type        = list(string)
  default     = ["203.0.113.0/24"] # RFC 5737 documentation range
}

variable "oidc_redirect_uris" {
  description = "Redirect URIs for the OIDC example app."
  type        = list(string)
  default     = ["https://oidcdebugger.com/debug"]
}

variable "saml_sp" {
  description = "Service provider details for the custom SAML example."
  type = object({
    acs_url   = string
    entity_id = string
  })
  default = {
    acs_url   = "https://sp.example.com/saml/acs"
    entity_id = "https://sp.example.com/saml/metadata"
  }
}

variable "scim" {
  description = "SCIM 2.0 target for the provisioning example. base_url empty = connection not managed here."
  type = object({
    sso_acs_url = string
    entity_id   = string
    base_url    = string
  })
  default = {
    sso_acs_url = "https://scim-sp.example.com/saml/acs"
    entity_id   = "https://scim-sp.example.com"
    base_url    = ""
  }
}

variable "scim_token" {
  description = "Bearer token for the SCIM target. Pass via TF_VAR_scim_token from a secret store."
  type        = string
  default     = ""
  sensitive   = true
}

variable "partner_idp" {
  description = "External SAML IdP for the just-in-time example. Empty issuer = pattern disabled."
  type = object({
    issuer        = string
    sso_url       = string
    signing_cert  = string # base64 DER (x5c), no PEM header
    email_domains = list(string)
  })
  default = {
    issuer        = ""
    sso_url       = ""
    signing_cert  = ""
    email_domains = []
  }
}
