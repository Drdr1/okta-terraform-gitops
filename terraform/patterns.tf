# One working example of each integration pattern. Copy a block to add an app.

module "oidc_example" {
  source = "../modules/oidc-app"

  label                    = "Example Portal (OIDC)"
  auth_server_name         = "example-api"
  audience                 = "api://example"
  custom_scopes            = { "example.read" = "Read example data" }
  redirect_uris            = var.oidc_redirect_uris
  assigned_group_ids       = [okta_group.this["engineering"].id]
  groups_claim_prefix      = "app_"
  authentication_policy_id = okta_app_signon_policy.standard.id
}

module "saml_example" {
  source = "../modules/saml-app"

  label                    = "Example Wiki (SAML)"
  acs_url                  = var.saml_sp.acs_url
  entity_id                = var.saml_sp.entity_id
  groups_attribute_regex   = "^(engineering|finance)$"
  assigned_group_ids       = [okta_group.this["engineering"].id, okta_group.this["finance"].id]
  authentication_policy_id = okta_app_signon_policy.standard.id
}

module "oin_example" {
  source = "../modules/oin-saml-app"

  catalog_name = "amazon_aws"
  label        = "AWS (OIN SAML)"
  settings = {
    appFilter          = "okta"
    awsEnvironmentType = "aws.amazon"
    joinAllRoles       = false
    loginURL           = "https://console.aws.amazon.com/"
    sessionDuration    = 3600
    useGroupMapping    = false
  }
  # Roles come from the IAM SAML provider; no per-group profile needed here.
  assigned_groups = [{
    id      = okta_group.this["app_admins"].id
    profile = {}
  }]
  authentication_policy_id = okta_app_signon_policy.standard.id
}

module "scim_example" {
  source = "../modules/scim-app"

  label                    = "Example SaaS (SAML + SCIM)"
  acs_url                  = var.scim.sso_acs_url
  entity_id                = var.scim.entity_id
  assigned_group_ids       = [okta_group.this["engineering"].id]
  authentication_policy_id = okta_app_signon_policy.standard.id

  # Flip to true in a PR after the console SCIM step (docs/patterns/04-scim.md).
  provisioning_enabled = false
  push_group_ids       = [okta_group.this["engineering"].id]

  # Only for apps on Okta's app-connections list (see the pattern doc).
  manage_connection = var.scim.base_url != ""
  scim_base_url     = var.scim.base_url
  scim_token        = var.scim_token
}

module "jit_example" {
  source = "../modules/jit-idp"
  count  = var.partner_idp.issuer == "" ? 0 : 1

  name          = "partner-saml"
  issuer        = var.partner_idp.issuer
  sso_url       = var.partner_idp.sso_url
  signing_cert  = var.partner_idp.signing_cert
  email_domains = var.partner_idp.email_domains
  jit_group_ids = [okta_group.this["contractors"].id]
}
