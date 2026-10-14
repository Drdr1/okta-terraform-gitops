# Pattern 3: Okta Integration Network (OIN) SAML app.
# The catalog decides the SAML details; we only set the app's own settings.
# Settings live in okta_app_saml_app_settings, not app_settings_json on the
# app, so a settings change is a small in-place update with a readable diff.

terraform {
  required_providers {
    okta = { source = "okta/okta" }
  }
}

resource "okta_app_saml" "this" {
  preconfigured_app     = var.catalog_name
  label                 = var.label
  status                = "ACTIVE"
  authentication_policy = var.authentication_policy_id

  lifecycle {
    # Managed by okta_app_saml_app_settings below.
    ignore_changes = [app_settings_json]
  }
}

resource "okta_app_saml_app_settings" "this" {
  app_id   = okta_app_saml.this.id
  settings = jsonencode(var.settings)
}

resource "okta_app_group_assignments" "this" {
  app_id = okta_app_saml.this.id

  dynamic "group" {
    for_each = var.assigned_groups
    content {
      id       = group.value.id
      priority = group.key + 1
      profile  = length(group.value.profile) > 0 ? jsonencode(group.value.profile) : null
    }
  }
}
