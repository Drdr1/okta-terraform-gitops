# okta-terraform-gitops

Okta Workforce Identity managed as code: every change is a pull request,
checked by CI and a plan guard, approved by a person, applied on merge.

Work sample by **Ahmed Darder** ([DerOps](https://derops.dev)).

```
PR ──► fmt · validate · tests ──► plan (read-only creds) ──► guard ──► plan comment
                                                                         │
merge ◄── code-owner approval ◄──────────────────────────────────────────┘
  │
  └──► re-plan from main ──► guard ──► [environment gate] ──► apply (non-prod org)

weekdays ──► read-only plan (nonprod; prod on demand) ──► must be empty, else drift issue
```

## What is here

| Path | What |
|---|---|
| `terraform/` | Root config for one org: groups + rules, network zones, an Identity Engine app sign-on policy, a password policy, and one example of each pattern |
| `modules/oidc-app` | OIDC web app + custom authorization server, scopes, groups claim, access policy |
| `modules/saml-app` | Custom SAML 2.0 app |
| `modules/oin-saml-app` | Okta Integration Network SAML app (example: AWS) |
| `modules/scim-app` | SAML SSO + SCIM 2.0 provisioning, enterprise attributes, group push |
| `modules/jit-idp` | External SAML IdP with just-in-time provisioning and routing by email domain |
| `tools/okta_discover.py` | Read-only discovery of an existing org → `import {}` blocks + list of what cannot be managed |
| `tools/plan_guard.py` | Plan summary for the PR; blocks deletes of groups/apps/policies; "no changes" mode for drift |
| `tools/gws_groups_inventory.py` | Read-only Google Groups inventory for the target group model |
| `.github/workflows/` | `ci` (no secrets), `okta` (plan on PR, apply on merge), `drift` (scheduled read-only plan) |
| `docs/` | [What is not managed](docs/NOT_MANAGED.md) · [patterns](docs/patterns) · [runbooks](docs/runbooks) · [Google Groups model](docs/google-groups-target-model.md) |

## Design choices

- **OAuth service apps, not API tokens.** `private_key_jwt`, one read-only
  app for plans and drift, one manage app only reachable from `main`.
  See [credentials](docs/runbooks/credentials.md).
- **Approval is the PR review** (CODEOWNERS + required `plan` check). A
  GitHub Environment can add a second approver before apply.
- **Re-plan on merge.** The PR plan can be stale; apply uses a fresh plan
  that passes the guard again.
- **Nothing destructive by accident.** `prevent_destroy` on groups, guard on
  deletes and replaces, `delete_target_group_on_destroy = false` on push groups.
- **Few secrets in state, and a locked-down state.** OIDC client secrets are
  omitted. The one exception is the SCIM token when `okta_app_connection`
  manages it; it comes in via `TF_VAR_*` from a secret store and ends up in
  state, so the state bucket uses CMEK, versioning, and IAM limited to the
  apply identity (plan gets read-only).

Provider traps found while building this are listed at the end of
[NOT_MANAGED.md](docs/NOT_MANAGED.md#provider-traps-found-while-building-this).

## Try it on a free org

1. Get a free org at developer.okta.com (Integrator Free Plan). Custom
   authorization servers need API Access Management on the org.
2. Create the two API service apps in [credentials](docs/runbooks/credentials.md).
3. Locally:
   ```bash
   export OKTA_ORG_NAME=integrator-1234567 OKTA_BASE_URL=okta.com
   export OKTA_API_CLIENT_ID=... OKTA_API_PRIVATE_KEY_ID=... OKTA_API_PRIVATE_KEY="$(cat key.pem)"
   export OKTA_API_SCOPES="okta.groups.manage,okta.apps.manage,okta.policies.manage,okta.networkZones.manage,okta.authorizationServers.manage,okta.idps.manage,okta.profileMappings.manage,okta.schemas.manage"
   cd terraform
   terraform init -backend=false     # local state for a quick try
   terraform plan -var-file=nonprod.tfvars
   ```
4. For the pipeline: set the GitHub environments and `OKTA_ENABLED=true`.

## Bring an existing org under code

```bash
python tools/okta_discover.py --out terraform/      # read-only
terraform -chdir=terraform plan -generate-config-out=generated.tf
```
Full, safe procedure: [import-existing](docs/runbooks/import-existing.md).

## Tests

```bash
pip install -r requirements.txt pytest && pytest -q
```

## Note on AI tools

Parts of this repo were drafted with an AI coding assistant. Every resource
argument was checked against the provider's own documentation for the pinned
version, and the Python tools are covered by tests.

## License

MIT
