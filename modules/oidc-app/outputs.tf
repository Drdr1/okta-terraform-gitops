output "app_id" {
  value = okta_app_oauth.this.id
}

output "client_id" {
  value = okta_app_oauth.this.client_id
}

output "issuer" {
  description = "Use <issuer>/.well-known/openid-configuration in the app."
  value       = okta_auth_server.this.issuer
}
