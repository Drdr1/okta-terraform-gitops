# Pattern 5: just-in-time provisioning from an external SAML IdP
# (a partner or acquired company). First sign-in creates the Okta user,
# adds them to the given groups, and later sign-ins update the profile.

terraform {
  required_providers {
    okta = { source = "okta/okta" }
  }
}

resource "okta_idp_saml_key" "this" {
  x5c = [var.signing_cert]
}

resource "okta_idp_saml" "this" {
  name                     = var.name
  issuer                   = var.issuer
  sso_url                  = var.sso_url
  sso_destination          = var.sso_url
  sso_binding              = "HTTP-POST"
  kid                      = okta_idp_saml_key.this.id
  acs_type                 = "INSTANCE"
  request_signature_scope  = "NONE"
  response_signature_scope = "ANY"

  # JIT: create on first sign-in; link to an existing user whose username
  # equals the SAML NameID (usually the email address).
  provisioning_action = "AUTO"
  username_template   = "idpuser.subjectNameId"
  subject_match_type  = "USERNAME"
  account_link_action = "AUTO"
  profile_master      = var.idp_is_profile_master

  groups_action     = "ASSIGN"
  groups_assignment = var.jit_group_ids

  deprovisioned_action = "NONE"
  suspended_action     = "NONE"
  status               = "ACTIVE"
}

# Route users of the partner's email domains to their IdP.
data "okta_policy" "idp_discovery" {
  name = "Idp Discovery Policy"
  type = "IDP_DISCOVERY"
}

resource "okta_policy_rule_idp_discovery" "this" {
  policy_id            = data.okta_policy.idp_discovery.id
  name                 = "route-${var.name}"
  priority             = var.routing_priority
  status               = "ACTIVE"
  network_connection   = "ANYWHERE"
  user_identifier_type = "IDENTIFIER"

  dynamic "user_identifier_patterns" {
    for_each = var.email_domains
    content {
      match_type = "SUFFIX"
      value      = "@${user_identifier_patterns.value}"
    }
  }

  idp_providers {
    id   = okta_idp_saml.this.id
    type = "SAML2"
  }
}
