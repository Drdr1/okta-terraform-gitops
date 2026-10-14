# Okta-mastered groups. Groups mastered by a directory or an app
# (type APP_GROUP, e.g. pushed from Google Workspace) are NOT managed here:
# Terraform would fight the sync. See docs/NOT_MANAGED.md.

locals {
  groups = {
    engineering = "All engineering staff. Membership by rule on user.department."
    finance     = "Finance team. Membership by rule on user.department."
    contractors = "Non-employees. Membership by rule on user.userType."
    app_admins  = "Admins of internal apps. Membership by PR only."
  }
}

resource "okta_group" "this" {
  for_each    = local.groups
  name        = each.key
  description = each.value

  lifecycle {
    # Deleting a group removes every app assignment that hangs off it.
    prevent_destroy = true
  }
}

resource "okta_group_rule" "by_department" {
  for_each = {
    engineering = "Engineering"
    finance     = "Finance"
  }

  name              = "dept-${each.key}"
  status            = "ACTIVE"
  group_assignments = [okta_group.this[each.key].id]
  expression_type   = "urn:okta:expression:1.0"
  expression_value  = "user.department == \"${each.value}\""
}

resource "okta_group_rule" "contractors" {
  name              = "usertype-contractor"
  status            = "ACTIVE"
  group_assignments = [okta_group.this["contractors"].id]
  expression_type   = "urn:okta:expression:1.0"
  expression_value  = "user.userType == \"Contractor\""
}
