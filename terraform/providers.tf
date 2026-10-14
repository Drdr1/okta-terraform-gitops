# Credentials come from the environment, never from tfvars:
#   OKTA_ORG_NAME, OKTA_BASE_URL            which org
#   OKTA_API_CLIENT_ID                      Okta API service app (OAuth 2.0)
#   OKTA_API_PRIVATE_KEY_ID, OKTA_API_PRIVATE_KEY   private_key_jwt signing key
#   OKTA_API_SCOPES                         read-only for plan, manage for apply
#
# No SSWS API token: it carries every permission of the admin who created
# it, cannot be limited to scopes, and lives until 30 days unused or revoked.
# See docs/runbooks/credentials.md.
provider "okta" {}
