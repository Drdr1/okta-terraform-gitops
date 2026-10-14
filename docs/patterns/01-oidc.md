# Pattern 1 — OIDC web app with a custom authorization server

**Use when** the app is your own or supports OIDC, and its API needs its own
audience and scopes. Module: `modules/oidc-app`.

**Creates:** auth server (one per API audience), custom scopes, a `groups`
ID-token claim filtered by name prefix, the web app (auth code + PKCE,
rotating refresh tokens), an access policy that lets only this client in,
a rule limited to the assigned groups, and the group assignments.

**Not in code:** the client secret (`omit_secret = true`). Copy it from the
console into the app's secret store, or switch the app to `private_key_jwt`.

**Test** (example uses https://oidcdebugger.com/debug as redirect URI):
1. `terraform output oidc_issuer` and `oidc_client_id`.
2. On oidcdebugger: authorize URI `<issuer>/v1/authorize`, scope
   `openid profile email example.read`, response type `code`, PKCE on.
3. Sign in as a member of `engineering` → code returned. A user outside
   the group is denied by the policy rule.
4. Add the test user to `app_admins` too, exchange the code, decode the ID
   token: `groups` holds `app_admins` and not `engineering` (prefix filter).
