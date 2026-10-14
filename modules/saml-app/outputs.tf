output "app_id" {
  value = okta_app_saml.this.id
}

output "metadata_url" {
  description = "Give this to the service provider."
  value       = okta_app_saml.this.metadata_url
}

output "idp_entity_id" {
  value = okta_app_saml.this.entity_url
}

output "idp_sso_url" {
  value = okta_app_saml.this.http_post_binding
}
