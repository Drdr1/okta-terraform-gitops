# Pipeline credentials

Two **API service apps** per org (Okta Admin Console → Applications →
API Services), each with **public key / private key** client authentication
(`private_key_jwt`). No SSWS API tokens: a token acts as the admin who made
it, has every permission that admin has, and is disabled only if that admin
leaves or someone remembers to revoke it.

| Service app | Used by | Okta API scopes |
|---|---|---|
| `terraform-<org>-plan` | PR plan, drift check | `okta.groups.read okta.apps.read okta.policies.read okta.networkZones.read okta.authorizationServers.read okta.idps.read okta.profileMappings.read okta.schemas.read` |
| `terraform-<org>-apply` | apply on `main` only | the same scopes with `.manage` |

Grant each app the smallest admin role that covers its scopes (a custom
admin role if the org has one; Read-only Admin for the plan app).

GitHub setup, per environment (`okta-nonprod-plan`, `okta-nonprod`, and
`okta-prod-plan` for read-only production drift checks):

- **vars:** `OKTA_ORG_NAME`, `OKTA_BASE_URL`, `OKTA_API_SCOPES`,
  `TF_STATE_BUCKET`, `GCP_WIF_PROVIDER`, `GCP_STATE_SA`
- **secrets:** `OKTA_API_CLIENT_ID`, `OKTA_API_PRIVATE_KEY_ID`, `OKTA_API_PRIVATE_KEY`
- `okta-nonprod` (apply): deployment branch = `main` only; required reviewers if the client wants a second approval.
- Repo variable `OKTA_ENABLED=true` turns the Okta jobs on.

## State bucket

- Keyless access: GitHub OIDC → Workload Identity Federation, no JSON keys.
- Two Google service accounts. The `*-plan` environments use one with
  **Storage Object Viewer** only; the apply environment uses one with
  object write. The WIF provider's attribute condition pins each SA to its
  GitHub environment (`assertion.environment`), so a PR that edits the
  workflow still cannot get write access to state.
- CMEK encryption, object versioning, and public access prevention. State
  can hold the SCIM token when `okta_app_connection` is used.

## Rotate a key (no downtime)

1. Generate a new key pair; add the public key to the service app (an app
   can hold two active keys).
2. Update `OKTA_API_PRIVATE_KEY` and `OKTA_API_PRIVATE_KEY_ID` in the environment.
3. Run the drift workflow by hand; it must pass.
4. Deactivate and delete the old public key in Okta.
