output "oidc_issuer" {
  value = module.oidc_example.issuer
}

output "oidc_client_id" {
  value = module.oidc_example.client_id
}

output "saml_metadata_url" {
  value = module.saml_example.metadata_url
}

output "oin_aws_metadata_url" {
  value = module.oin_example.metadata_url
}

output "scim_app_id" {
  value = module.scim_example.app_id
}
