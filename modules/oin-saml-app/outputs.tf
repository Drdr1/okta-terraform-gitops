output "app_id" {
  value = okta_app_saml.this.id
}

output "metadata_url" {
  value = okta_app_saml.this.metadata_url
}
