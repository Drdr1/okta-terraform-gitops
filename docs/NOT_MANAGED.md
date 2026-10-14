# What Terraform does not manage here

Checked against Okta provider 6.15. `tools/okta_discover.py` writes the
org-specific list to `unmanaged.md`; this page explains each category.

| Object | Why it stays out | What we do instead |
|---|---|---|
| `Everyone` group | Built in, cannot be created or deleted | `data "okta_group"` |
| Groups mastered by Google Workspace, AD or an app (`APP_GROUP`) | The directory sync owns them; Terraform would fight it | `data "okta_group"`; change membership at the source |
| Okta first-party apps (Admin Console, Dashboard, Browser Plugin, Workflows) | Exist in every org, not owned by us | Leave in console |
| Apps with no matching resource (e.g. WS-Federation) | No provider resource for that sign-on mode | Console, listed in `unmanaged.md`, reviewed each quarter |
| Default global session policy, default access policy | Cannot be created or deleted | Manage their non-system rules in code |
| System / catch-all rules | Cannot be created or deleted | Edit in console; keep the setting in the runbook |
| Default password and MFA enrollment policies | — | **Managed** with `okta_policy_password_default` / `okta_policy_mfa_default` (import id `.`) |
| System network zones (`LegacyIpZone`, `BlockedIpZone`, default dynamic zones) | Cannot be deleted; importing invites accidental destroy | Console; add our own zones in code |
| SCIM connection on **custom** (AIW) apps: base URL, auth header, To App toggles | `okta_app_connection` / `okta_app_features` only support a set of OIN apps | One console step per app, then everything else in code (see patterns/04-scim.md) |
| OIDC client secrets | Would sit in plain text in state | `omit_secret = true`; secret lives in the app's secret store |
| Users and direct user-to-app assignments | Out of scope; access is by group | Move to group assignment before import |
| Okta Workflows flows, Identity Governance campaigns | Out of scope this phase | Console |

## Provider traps found while building this

- `okta_app_oauth.groups_claim` is **silently skipped** when the provider uses
  OAuth credentials. Use `okta_auth_server_claim` instead.
- `okta_push_group.delete_target_group_on_destroy` defaults to **true**:
  removing the mapping deletes the group in the downstream app. Set it to
  `false` everywhere.
- `okta_app_oauth` stores `client_secret` in state unless `omit_secret = true`.
- `okta_app_saml.app_settings_json` on OIN apps produces noisy diffs. Use
  `okta_app_saml_app_settings` and `ignore_changes = [app_settings_json]`.
- `okta_profile_mapping` with `delete_when_absent = true` wipes every mapping
  you did not list, including the base ones Okta creates.
- The provider's GitHub README (Oct 2026) warns against 6.14.0 and names
  6.15.0 as the highest recommended release, although 7.0.0 is out. The
  version is pinned, the lock file is committed, and bumps get their own PR.
- A password policy with no rule is ignored by Okta; users fall through to
  the next policy. Every `okta_policy_password` here has a rule.
