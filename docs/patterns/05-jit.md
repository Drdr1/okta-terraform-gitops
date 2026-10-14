# Pattern 5 — just-in-time provisioning from an external SAML IdP

**Use when** people from a partner or an acquired company should sign in
with their own IdP and get an Okta account on first sign-in. Module:
`modules/jit-idp`. (For JIT into a downstream app, use that app's own JIT
setting; this pattern is JIT into Okta.)

**Creates:** the IdP signing key, a SAML IdP with
`provisioning_action = AUTO` (create on first login), account linking by
username, group assignment (`contractors`) on every login, and an IdP
routing rule that sends the partner's email domains to their IdP.

**Inputs from the partner:** issuer (entity ID), SSO URL (HTTP-POST),
signing certificate. Set them in `partner_idp` in the tfvars; empty issuer
keeps the pattern off.

**Give the partner:** ACS URL `https://<okta-domain>/sso/saml2/<idp_id>`
and the audience from `terraform output`.

**Test:** a second free Okta org works as the partner IdP. Sign in with a
user `@partner-domain` → routed to the partner, back with a new Okta user in
`contractors`. Change their name at the partner → updated on next sign-in
(`idp_is_profile_master = true`).
