# Google Groups → Okta target model (worksheet)

Input: `tools/gws_groups_inventory.py` (read-only) → `groups.csv`,
`memberships.csv`, `report.md`. Run it in the client's approved environment.

## Decide per group

| Google group pattern | Okta target |
|---|---|
| Department / role list that matches HR data | Okta group filled by a **group rule** on a profile attribute |
| Hand-picked access list for one app | Okta group, membership by PR or request workflow; app assignment in code |
| Mailing / collaboration list | Stays in Google only; not an Okta group |
| Nested groups | Flatten. Okta rules and assignments do not follow nesting |
| Groups with external members | Contractors get Okta accounts (or JIT from their IdP); the group is rebuilt from those |
| Empty or no owner | Retire after owner check |

## Naming

`<type>_<scope>_<purpose>`: `dept_engineering`, `app_jira_admins`,
`role_oncall`. The OIDC groups claim filters on the `app_` prefix, so apps
only see their own groups.

## Output

A table with one row per surviving Google group: target Okta group, rule
expression or "manual", owner, apps it grants. That table becomes
`terraform/groups.tf` in the next phase.
