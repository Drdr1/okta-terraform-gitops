# Pattern 1: OIDC web app behind its own custom authorization server.
# One auth server per API audience; apps that call the same API share it.

terraform {
  required_providers {
    okta = { source = "okta/okta" }
  }
}

resource "okta_auth_server" "this" {
  name        = var.auth_server_name
  description = "Issues tokens for ${var.audience}"
  audiences   = [var.audience]
  issuer_mode = "ORG_URL"
  status      = "ACTIVE"
}

resource "okta_auth_server_scope" "custom" {
  for_each         = var.custom_scopes
  auth_server_id   = okta_auth_server.this.id
  name             = each.key
  description      = each.value
  consent          = "IMPLICIT"
  metadata_publish = "NO_CLIENTS"
}

# Groups go in the ID token through the auth server, not the app's
# `groups_claim` block: that block is deprecated and is silently skipped
# when the provider authenticates with OAuth (which this repo does).
resource "okta_auth_server_claim" "groups" {
  auth_server_id    = okta_auth_server.this.id
  name              = "groups"
  claim_type        = "IDENTITY"
  value_type        = "GROUPS"
  group_filter_type = "STARTS_WITH"
  value             = var.groups_claim_prefix
  scopes            = ["openid"]
}

resource "okta_app_oauth" "this" {
  label                      = var.label
  type                       = "web"
  grant_types                = ["authorization_code", "refresh_token"]
  response_types             = ["code"]
  redirect_uris              = var.redirect_uris
  post_logout_redirect_uris  = var.post_logout_redirect_uris
  token_endpoint_auth_method = "client_secret_basic"
  pkce_required              = true
  refresh_token_rotation     = "ROTATE"
  refresh_token_leeway       = 30
  authentication_policy      = var.authentication_policy_id

  # Keep the client secret out of Terraform state. Read or rotate it in
  # the Admin Console and hand it to the app's own secret store.
  omit_secret = true
}

resource "okta_auth_server_policy" "this" {
  auth_server_id   = okta_auth_server.this.id
  name             = "${var.label} access"
  description      = "Only ${var.label} may get tokens from this policy."
  priority         = 1
  status           = "ACTIVE"
  client_whitelist = [okta_app_oauth.this.client_id]
}

resource "okta_auth_server_policy_rule" "this" {
  auth_server_id                 = okta_auth_server.this.id
  policy_id                      = okta_auth_server_policy.this.id
  name                           = "assigned-groups"
  priority                       = 1
  status                         = "ACTIVE"
  grant_type_whitelist           = ["authorization_code"]
  group_whitelist                = var.assigned_group_ids
  scope_whitelist                = concat(["openid", "profile", "email", "offline_access"], keys(var.custom_scopes))
  access_token_lifetime_minutes  = 60
  refresh_token_lifetime_minutes = 1440
  refresh_token_window_minutes   = 480
}

resource "okta_app_group_assignments" "this" {
  app_id = okta_app_oauth.this.id

  dynamic "group" {
    for_each = var.assigned_group_ids
    content {
      id       = group.value
      priority = group.key + 1
    }
  }
}
