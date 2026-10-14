#!/usr/bin/env python3
"""Check a Terraform plan before a human reviews it.

Reads `terraform show -json tfplan` output and:
  * writes a short Markdown summary for the PR comment
  * fails on deletes/replaces of objects users depend on, unless the PR
    carries the `allow-destroy` label (ALLOW_DESTROY=true)
  * in --expect-no-changes mode (production drift check), fails on ANY change

Exit codes: 0 ok, 1 blocked, 2 bad input.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

# Removing any of these cuts users off from apps or sign-in.
PROTECTED_PREFIXES = (
    "okta_group",            # also okta_group_rule
    "okta_app_",
    "okta_auth_server",
    "okta_idp_",
    "okta_policy",
    "okta_network_zone",
    "okta_push_group",
)


def action_of(change: dict) -> str:
    acts = change["change"]["actions"]
    if acts == ["no-op"] or acts == ["read"]:
        return "no-op"
    if acts == ["create"]:
        return "create"
    if acts == ["update"]:
        return "update"
    if acts == ["delete"]:
        return "delete"
    if sorted(acts) == ["create", "delete"]:
        return "replace"
    return "+".join(acts)


def evaluate(plan: dict, allow_destroy: bool = False, expect_no_changes: bool = False):
    """Return (summary_markdown, problems). Pure."""
    changes = []
    for rc in plan.get("resource_changes", []):
        act = action_of(rc)
        if act != "no-op":
            changes.append((act, rc["address"], rc["type"]))

    drift = [d["address"] for d in plan.get("resource_drift", [])]
    counts = Counter(a for a, _, _ in changes)

    problems: list[str] = []
    if expect_no_changes and changes:
        problems.append(f"Expected no changes, plan has {len(changes)}.")
    for act, addr, rtype in changes:
        if act in ("delete", "replace") and rtype.startswith(PROTECTED_PREFIXES) and not allow_destroy:
            problems.append(f"{act} of protected object `{addr}` (add the `allow-destroy` label if intended)")

    lines = ["### Okta plan", ""]
    if not changes:
        lines.append("No changes. Okta matches the code.")
    else:
        lines.append(" · ".join(f"**{counts[k]}** to {k}" for k in ("create", "update", "replace", "delete") if counts[k]))
        lines.append("")
        lines.append("| Action | Resource |")
        lines.append("|---|---|")
        order = {"delete": 0, "replace": 1, "update": 2, "create": 3}
        for act, addr, _ in sorted(changes, key=lambda c: (order.get(c[0], 9), c[1])):
            lines.append(f"| {act} | `{addr}` |")
    if drift:
        lines += ["", f"Changed outside Terraform since last apply: {len(drift)} object(s)."]
        lines += [f"- `{a}`" for a in drift[:20]]
    if problems:
        lines += ["", "**Blocked:**"] + [f"- {p}" for p in problems]
    return "\n".join(lines) + "\n", problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan_json", help="output of: terraform show -json tfplan")
    ap.add_argument("--summary", help="write Markdown summary here")
    ap.add_argument("--expect-no-changes", action="store_true")
    args = ap.parse_args(argv)

    try:
        plan = json.loads(Path(args.plan_json).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"cannot read plan: {exc}", file=sys.stderr)
        return 2

    allow = os.environ.get("ALLOW_DESTROY", "").lower() == "true"
    summary, problems = evaluate(plan, allow_destroy=allow, expect_no_changes=args.expect_no_changes)
    if args.summary:
        Path(args.summary).write_text(summary)
    print(summary)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
