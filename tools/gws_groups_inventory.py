#!/usr/bin/env python3
"""Read-only inventory of Google Workspace groups, as input to the Okta
target group model (docs/google-groups-target-model.md).

Auth: a service account with domain-wide delegation, impersonating a
read-only admin. Scopes requested are read-only only:
  admin.directory.group.readonly
  admin.directory.group.member.readonly

Run it inside the client's approved environment; the CSVs contain names
and email addresses.

Usage:
  GOOGLE_APPLICATION_CREDENTIALS=sa.json \\
  python tools/gws_groups_inventory.py --admin reader@corp.com --domain corp.com --out inventory/
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

API = "https://admin.googleapis.com/admin/directory/v1"
SCOPES = [
    "https://www.googleapis.com/auth/admin.directory.group.readonly",
    "https://www.googleapis.com/auth/admin.directory.group.member.readonly",
]


def paged(session, url: str, key: str, params: dict | None = None):
    params = dict(params or {})
    while True:
        resp = session.get(url, params=params, timeout=60)
        resp.raise_for_status()
        body = resp.json()
        yield from body.get(key, [])
        token = body.get("nextPageToken")
        if not token:
            return
        params["pageToken"] = token


def fetch(session) -> tuple[list[dict], dict[str, list[dict]]]:
    groups = list(paged(session, f"{API}/groups", "groups", {"customer": "my_customer", "maxResults": 200}))
    members = {
        g["email"].lower(): list(paged(session, f'{API}/groups/{g["id"]}/members', "members", {"maxResults": 200}))
        for g in groups
    }
    return groups, members


def nesting_depth(group: str, members: dict[str, list[dict]], seen: frozenset = frozenset()) -> int:
    """Levels of groups-inside-groups below `group`. Cycles count once."""
    if group in seen:
        return 0
    children = [m["email"].lower() for m in members.get(group, []) if m.get("type") == "GROUP"]
    if not children:
        return 0
    return 1 + max(nesting_depth(c, members, seen | {group}) for c in children)


def summarize(groups: list[dict], members: dict[str, list[dict]], domains: list[str]) -> dict:
    """Per-group facts plus org-wide counts. Pure."""
    internal = tuple("@" + d.lower() for d in domains)
    rows = []
    for g in sorted(groups, key=lambda g: g["email"].lower()):
        email = g["email"].lower()
        ms = members.get(email, [])
        users = [m for m in ms if m.get("type") == "USER"]
        external = [m for m in users if internal and not m.get("email", "").lower().endswith(internal)]
        rows.append({
            "email": email,
            "name": g.get("name", ""),
            "description": (g.get("description") or "").replace("\n", " "),
            "direct_users": len(users),
            "nested_groups": sum(1 for m in ms if m.get("type") == "GROUP"),
            "external_users": len(external),
            "whole_domain": any(m.get("type") == "CUSTOMER" for m in ms),
            "owners": sum(1 for m in ms if m.get("role") == "OWNER"),
            "depth": nesting_depth(email, members),
            "admin_created": bool(g.get("adminCreated", True)),
        })
    totals = Counter()
    for r in rows:
        totals["groups"] += 1
        totals["empty"] += r["direct_users"] == 0 and r["nested_groups"] == 0 and not r["whole_domain"]
        totals["with_external_users"] += r["external_users"] > 0
        totals["nested"] += r["nested_groups"] > 0
        totals["no_owner"] += r["owners"] == 0
        totals["user_created"] += not r["admin_created"]
    totals["max_depth"] = max((r["depth"] for r in rows), default=0)
    return {"rows": rows, "totals": dict(totals)}


def render_report(summary: dict) -> str:
    t = summary["totals"]
    out = [
        "# Google Groups inventory",
        "",
        f"- Groups: **{t.get('groups', 0)}**",
        f"- Empty: {t.get('empty', 0)}",
        f"- With external members: {t.get('with_external_users', 0)}",
        f"- Contain other groups: {t.get('nested', 0)} (deepest nesting: {t.get('max_depth', 0)})",
        f"- No owner: {t.get('no_owner', 0)}",
        f"- Created by users, not admins: {t.get('user_created', 0)}",
        "",
        "Okta group rules and app assignments do not follow Google nesting.",
        "Every nested group needs a decision: flatten, or model as a rule.",
        "",
        "| Group | Users | Nested | External | Depth |",
        "|---|---|---|---|---|",
    ]
    for r in summary["rows"]:
        if r["nested_groups"] or r["external_users"] or r["whole_domain"]:
            out.append(f'| {r["email"]} | {r["direct_users"]} | {r["nested_groups"]} | {r["external_users"]} | {r["depth"]} |')
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--admin", help="Read-only admin to impersonate")
    ap.add_argument("--domain", action="append", default=[], help="Internal domain (repeat)")
    ap.add_argument("--out", default="inventory")
    ap.add_argument("--from-json", help="Use a saved {groups, members} snapshot")
    args = ap.parse_args(argv)

    if args.from_json:
        snap = json.loads(Path(args.from_json).read_text())
        groups, members = snap["groups"], snap["members"]
    else:
        if not args.admin:
            ap.error("--admin is required when reading from Google")
        import google.auth
        from google.auth.transport.requests import AuthorizedSession

        creds, _ = google.auth.default(scopes=SCOPES)
        creds = creds.with_subject(args.admin)
        groups, members = fetch(AuthorizedSession(creds))

    summary = summarize(groups, members, args.domain)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "groups.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary["rows"][0].keys()) if summary["rows"] else ["email"])
        w.writeheader()
        w.writerows(summary["rows"])
    with open(out / "memberships.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["group", "member", "type", "role", "status"])
        for g, ms in sorted(members.items()):
            for m in ms:
                w.writerow([g, m.get("email", m.get("id", "")), m.get("type"), m.get("role"), m.get("status", "")])
    (out / "report.md").write_text(render_report(summary))
    print(render_report(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
