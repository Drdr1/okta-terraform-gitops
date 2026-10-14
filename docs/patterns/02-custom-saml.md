# Pattern 2 — custom SAML app

**Use when** the vendor supports SAML but is not in the Okta Integration
Network. Module: `modules/saml-app`.

**Needs from the vendor:** ACS URL and entity ID (audience). Ask for the
NameID format they match on; the default here is email.

**Creates:** signed response and assertion (RSA-SHA256), NameID = email,
attributes `email`, `firstName`, `lastName`, an optional `groups` attribute
filtered by regex, group assignments, and the shared sign-on policy.

**Hand to the vendor:** `terraform output saml_metadata_url`.

**Test:** point any SAML SP test tool at the metadata URL, start SP-initiated
login, and check the assertion: audience, recipient, NameID, attributes,
and that a user outside the assigned groups gets "not assigned".

**Common failures:** ACS URL with a trailing slash mismatch; vendor expects
`unspecified` NameID format; vendor caches old metadata after a cert rotation.
