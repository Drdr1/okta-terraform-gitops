# Pattern 2: custom SAML 2.0 app (App Integration Wizard style).

terraform {
  required_providers {
    okta = { source = "okta/okta" }
  }
}

resource "okta_app_saml" "this" {
  label                    = var.label
  sso_url                  = var.acs_url
  recipient                = var.acs_url
  destination              = var.acs_url
  audience                 = var.entity_id
  subject_name_id_template = "$${user.email}"
  subject_name_id_format   = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
  response_signed          = true
  assertion_signed         = true
  signature_algorithm      = "RSA_SHA256"
  digest_algorithm         = "SHA256"
  honor_force_authn        = true
  authn_context_class_ref  = "urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport"
  authentication_policy    = var.authentication_policy_id

  dynamic "attribute_statements" {
    for_each = var.attributes
    content {
      type      = "EXPRESSION"
      name      = attribute_statements.key
      namespace = "urn:oasis:names:tc:SAML:2.0:attrname-format:basic"
      values    = [attribute_statements.value]
    }
  }

  dynamic "attribute_statements" {
    for_each = var.groups_attribute_regex == null ? [] : [var.groups_attribute_regex]
    content {
      type         = "GROUP"
      name         = "groups"
      namespace    = "urn:oasis:names:tc:SAML:2.0:attrname-format:basic"
      filter_type  = "REGEX"
      filter_value = attribute_statements.value
    }
  }
}

resource "okta_app_group_assignments" "this" {
  app_id = okta_app_saml.this.id

  dynamic "group" {
    for_each = var.assigned_group_ids
    content {
      id       = group.value
      priority = group.key + 1
    }
  }
}
