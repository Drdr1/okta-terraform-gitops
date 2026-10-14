# Bring an existing org into Terraform

Goal: every manageable object is in code, and a read-only plan against the
org shows **no changes**. Nothing is written to the org at any step.

1. **Freeze.** Announce a change freeze on the objects being imported. Ask
   admins to log console changes in the PR channel until step 9.
2. **Read-only credentials.** Use the `*-plan` service app (read scopes only,
   see credentials.md). The import cannot change Okta even by mistake.
3. **Discover.**
   `python tools/okta_discover.py --out terraform/ --save-json inv.json`
   → `imports.tf` (one `import {}` block per object) and `unmanaged.md`.
4. **Review `unmanaged.md`** with the client. Each line gets a decision:
   leave in console, data source, or fix first (e.g. move direct user
   assignments to a group).
5. **Import in batches by type** — groups, rules, zones, auth servers,
   policies, then apps. Smaller PRs, easier review, and a bad batch is easy
   to drop. Keep only that batch's blocks in `imports.tf`.
6. **Generate HCL.**
   `terraform plan -generate-config-out=generated.tf -var-file=prod.tfvars`
7. **Clean the HCL until the plan is empty.** Typical fixes: remove computed
   or conflicting attributes the generator wrote, replace IDs with references
   (`okta_group.eng.id`), move OIN settings to `okta_app_saml_app_settings`,
   move into modules with `moved {}` blocks. Repeat plan until it says
   *No changes* except the import lines.
8. **Merge and apply the import.** Label the PR `import-only`: the guard then
   fails on any change besides the imports. Apply only records the objects in
   state; Okta itself is not touched.
9. **Prove it.** Run the drift workflow against the org. It must pass with
   zero changes. Delete `imports.tf`, lift the freeze.

For production, the same steps run with the `okta-prod-plan` environment
(read-only) and `prod.tfvars`; the import apply for production is a
separate, approved job outside this sample.

Add `lifecycle { prevent_destroy = true }` to groups, apps and auth servers
during import. Removing a block from code must never delete a live object
by accident.
