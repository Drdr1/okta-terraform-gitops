# Pattern 4: SAML SSO + SCIM 2.0 provisioning for a custom app.
#
# Split of work (see docs/patterns/04-scim.md):
#   Terraform: the app, assignments, custom app attributes, Okta->app
#              mappings for those attributes, and group push.
#   One-time console step on custom (AIW) apps: Provisioning = SCIM,
#              base URL, auth header, and the To App toggles.
#   okta_app_connection only for apps on Okta's app-connections list.

terraform {
  required_providers {
    okta = { source = "okta/okta" }
  }
}

module "sso" {
  source = "../saml-app"

  label                    = var.label
  acs_url                  = var.acs_url
  entity_id                = var.entity_id
  assigned_group_ids       = var.assigned_group_ids
  authentication_policy_id = var.authentication_policy_id
}

# SCIM enterprise extension attributes, sent on create and update.
resource "okta_app_user_schema_property" "enterprise" {
  for_each = var.enterprise_attributes

  app_id             = module.sso.app_id
  index              = each.key
  title              = each.key
  type               = "string"
  master             = "OKTA"
  scope              = "NONE"
  external_name      = each.key
  external_namespace = "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
}

data "okta_user_profile_mapping_source" "okta_user" {}

# Only the attributes this module owns. delete_when_absent = false so the
# base mappings Okta creates when SCIM is switched on are left alone.
resource "okta_profile_mapping" "to_app" {
  count = var.provisioning_enabled ? 1 : 0

  source_id          = data.okta_user_profile_mapping_source.okta_user.id
  target_id          = module.sso.app_id
  delete_when_absent = false

  dynamic "mappings" {
    for_each = var.enterprise_attributes
    content {
      id          = mappings.key
      expression  = mappings.value
      push_status = "PUSH"
    }
  }

  depends_on = [okta_app_user_schema_property.enterprise]
}

resource "okta_push_group" "this" {
  for_each = var.provisioning_enabled ? toset(var.push_group_ids) : toset([])

  app_id          = module.sso.app_id
  source_group_id = each.value
  status          = "ACTIVE"

  # Provider default is true: removing this mapping would delete the group
  # (and its memberships) in the downstream app. Unlinking must not do that.
  delete_target_group_on_destroy = false
}

resource "okta_app_connection" "this" {
  count = var.manage_connection ? 1 : 0

  id       = module.sso.app_id
  base_url = var.scim_base_url
  action   = "activate"

  profile {
    auth_scheme = "TOKEN"
    token       = var.scim_token # stored in state: keep the state bucket encrypted and tightly scoped
  }

  lifecycle {
    precondition {
      condition     = var.scim_base_url != "" && var.scim_token != ""
      error_message = "manage_connection needs scim_base_url and scim_token."
    }
  }
}
