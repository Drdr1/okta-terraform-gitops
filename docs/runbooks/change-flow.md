# Make a change

1. Branch from `main`, edit HCL. Copy a block from `terraform/patterns.tf`
   for a new app.
2. Open a PR. CI runs `fmt`, `validate`, tests, and a plan against the
   non-production org with read-only credentials.
3. Read the plan comment. The guard blocks deletes and replacements of
   groups, apps, policies, zones, IdPs and auth servers. If that is really
   intended, add the `allow-destroy` label and say why in the PR.
4. A code owner approves. This is the approval that counts.
5. Merge. `apply` re-plans from `main`, runs the guard again, and applies.
6. Check the job summary. If apply failed half-way, re-run the job: the next
   plan shows what is left.

## Someone changed Okta in the console

The drift workflow opens an issue named `Okta drift: <org>`. Then either:

- **Keep the console change:** copy it into HCL in a PR until the plan shows
  no changes, or
- **Undo it:** run the normal PR flow; apply puts Okta back to the code.

Objects **created** in the console are not in state, so the drift plan
cannot see them. Once a month, run `tools/okta_discover.py` against the org:
any import block for an object not already in code is a console-created
object to adopt or remove.

## Emergency (break glass)

Make the fix in the console, then within one business day open a PR that
makes the code match. The drift issue is the reminder; close it with that PR.
