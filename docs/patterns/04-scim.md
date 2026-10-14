# Pattern 4 — SAML SSO + SCIM 2.0 provisioning

**Use when** the app should get users and groups created, updated and
deactivated by Okta. Module: `modules/scim-app`.

**Order of work for a custom SCIM app:**
1. PR 1: create the app with `provisioning_enabled = false`.
2. Console, once: General → Provisioning: **SCIM**. Provisioning tab:
   base URL, auth (HTTP header bearer token), Test → Save. To App: enable
   Create, Update, Deactivate. This is the step Terraform cannot do for
   custom apps (see NOT_MANAGED.md).
3. PR 2: set `provisioning_enabled = true`. Terraform adds the enterprise
   attributes (`department`, `costCenter`), maps them from the Okta profile
   with push on update, and pushes the chosen groups.

For OIN apps on Okta's app-connections list, set `scim.base_url` in the
tfvars and pass the token through `TF_VAR_scim_token` from a secret store;
step 2 then happens in code. The token is stored in state, which is why
the state bucket is locked down (see credentials.md).

**Safety:** `delete_target_group_on_destroy = false` on every push group;
the provider default would delete the group in the target app.

**Test:** run a local SCIM test server (any SCIM 2.0 mock) behind HTTPS,
assign a test user via `engineering`, check the POST /Users body has the
enterprise extension, change `department` in Okta, see PATCH, unassign,
see `active: false`.
