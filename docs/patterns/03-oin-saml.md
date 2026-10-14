# Pattern 3 — Okta Integration Network (OIN) SAML app

**Use when** the app is in the OIN catalog. The catalog owns the SAML
details; we set only the app's own settings. Module: `modules/oin-saml-app`.
Example: `amazon_aws` (AWS Account Federation).

**Find the settings for a new OIN app:** add it once by hand in the sandbox,
then `GET /api/v1/apps/{id}` → `name` is `catalog_name`, `settings.app` is
`settings`. Delete the hand-made app and create it from code.

**Why a separate settings resource:** `okta_app_saml_app_settings` gives a
small readable diff and stops `app_settings_json` from showing changes on
every plan.

**Test (AWS):** download `terraform output oin_aws_metadata_url`, create an
IAM SAML provider named `OKTA` with it, create a role trusting that
provider, then sign in from the Okta dashboard and pick the role.
