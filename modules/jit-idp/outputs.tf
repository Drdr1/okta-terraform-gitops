output "idp_id" {
  description = "The partner's ACS URL is https://<okta-domain>/sso/saml2/<idp_id>."
  value       = okta_idp_saml.this.id
}

output "audience" {
  description = "Audience (SP entity ID) the partner IdP must use."
  value       = okta_idp_saml.this.audience
}
