# Identity Engine app sign-on (authentication) policy shared by the example
# apps. One policy per risk tier keeps the number of policies small.

resource "okta_app_signon_policy" "standard" {
  name        = "standard-apps"
  description = "Default tier: two factors everywhere, shorter sessions off-network."
}

resource "okta_app_signon_policy_rule" "office_2fa" {
  policy_id                   = okta_app_signon_policy.standard.id
  name                        = "office-network-2fa"
  priority                    = 1
  network_connection          = "ZONE"
  network_includes            = [okta_network_zone.office.id]
  factor_mode                 = "2FA"
  re_authentication_frequency = "PT12H"
}

resource "okta_app_signon_policy_rule" "offsite_2fa_short" {
  policy_id                   = okta_app_signon_policy.standard.id
  name                        = "off-network-2fa-short-session"
  priority                    = 2
  network_connection          = "ANYWHERE"
  factor_mode                 = "2FA"
  re_authentication_frequency = "PT2H"
}

resource "okta_policy_password" "contractors" {
  name                   = "contractors-password"
  description            = "Stricter password policy for non-employees."
  status                 = "ACTIVE"
  priority               = 1
  groups_included        = [okta_group.this["contractors"].id]
  password_min_length    = 14
  password_history_count = 12
  # No forced expiry (NIST SP 800-63B); breached-password checks instead.
  password_dictionary_lookup = true
}

# A password policy without a rule is skipped by Okta.
resource "okta_policy_rule_password" "contractors" {
  policy_id       = okta_policy_password.contractors.id
  name            = "contractors-self-service"
  priority        = 1
  status          = "ACTIVE"
  password_change = "ALLOW"
  password_reset  = "ALLOW"
  password_unlock = "DENY"
}
