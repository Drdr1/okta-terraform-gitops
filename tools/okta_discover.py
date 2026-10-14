#!/usr/bin/env python3
"""Discover an existing Okta org and write Terraform `import` blocks.

Read-only. Produces two files:
  imports.tf     one `import {}` block per object Terraform can manage
  unmanaged.md   everything left out, with the reason

Then run `terraform plan -generate-config-out=generated.tf` to get a first
draft of the HCL. See docs/runbooks/import-existing.md for the full flow.

Usage:
  python tools/okta_discover.py --out terraform/          # live org
  python tools/okta_discover.py --from-json inv.json ...  # saved inventory
  python tools/okta_discover.py --save-json inv.json ...  # keep a snapshot
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import requests

# Okta first-party apps. They exist in every org and are not yours to manage.
FIRST_PARTY_APPS = {
    "saasure",               # Admin Console
    "okta_enduser",          # End-User Dashboard
    "okta_browser_plugin",
    "okta_flow_sso",         # Workflows
}

APP_TYPES = {
    "SAML_2_0": "okta_app_saml",
    "SAML_1_1": "okta_app_saml",
    "OPENID_CONNECT": "okta_app_oauth",
    "BOOKMARK": "okta_app_bookmark",
    "AUTO_LOGIN": "okta_app_auto_login",
    "BASIC_AUTH": "okta_app_basic_auth",
    "BROWSER_PLUGIN": "okta_app_swa",
    "SECURE_PASSWORD_STORE": "okta_app_secure_password_store",
}

# policy type -> (policy resource, rule resource, default-policy resource)
POLICY_TYPES = {
    "OKTA_SIGN_ON": ("okta_policy_signon", "okta_policy_rule_signon", None),
    "PASSWORD": ("okta_policy_password", "okta_policy_rule_password", "okta_policy_password_default"),
    "MFA_ENROLL": ("okta_policy_mfa", "okta_policy_rule_mfa", "okta_policy_mfa_default"),
    "ACCESS_POLICY": ("okta_app_signon_policy", "okta_app_signon_policy_rule", None),
    "PROFILE_ENROLLMENT": ("okta_policy_profile_enrollment", "okta_policy_rule_profile_enrollment", None),
}

IDP_TYPES = {"SAML2": "okta_idp_saml", "OIDC": "okta_idp_oidc"}
SOCIAL_IDPS = {"GOOGLE", "FACEBOOK", "MICROSOFT", "LINKEDIN", "APPLE", "GITHUB", "GITLAB", "AMAZON", "DISCORD", "PAYPAL", "SALESFORCE", "SPOTIFY", "XERO", "YAHOO"}


# Keys whose values are secrets in Okta API responses. Removed before an
# inventory is written to disk.
SECRET_KEYS = {"client_secret", "password", "token", "secret", "signing_secret", "private_key"}


def redact(obj):
    """Copy of an API response with secret values replaced. `kid` is kept."""
    if isinstance(obj, dict):
        return {k: ("<redacted>" if k.lower() in SECRET_KEYS and not isinstance(v, (dict, list)) else redact(v))
                for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(v) for v in obj]
    return obj


@dataclass(frozen=True)
class Import:
    resource: str
    name: str
    id: str
    label: str


@dataclass(frozen=True)
class Unmanaged:
    kind: str
    label: str
    id: str
    reason: str


@dataclass
class Result:
    imports: list[Import] = field(default_factory=list)
    unmanaged: list[Unmanaged] = field(default_factory=list)


def slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_") or "unnamed"
    return f"x_{s}" if s[0].isdigit() else s


class Namer:
    """Stable, unique Terraform names per resource type.

    Same name twice -> the second gets the last 6 chars of its Okta id, so
    names do not shift when a new object is added to the org.
    """

    def __init__(self) -> None:
        self.used: dict[str, set[str]] = {}

    def name(self, resource: str, text: str, okta_id: str) -> str:
        used = self.used.setdefault(resource, set())
        base = slug(text)
        candidate = base if base not in used else f"{base}_{okta_id[-6:].lower()}"
        n = 2
        while candidate in used:
            candidate = f"{base}_{okta_id[-6:].lower()}_{n}"
            n += 1
        used.add(candidate)
        return candidate


def _sorted(items, key):
    return sorted(items, key=lambda o: (key(o) or "", o.get("id", "")))


def build(inv: dict) -> Result:
    """Turn a raw inventory into import blocks and an unmanaged list. Pure."""
    r = Result()
    names = Namer()

    def add(resource: str, label: str, okta_id: str, import_id: str | None = None, name_text: str | None = None):
        tf_name = names.name(resource, name_text or label, okta_id)
        r.imports.append(Import(resource, tf_name, import_id or okta_id, label))
        return tf_name

    def skip(kind: str, label: str, okta_id: str, reason: str):
        r.unmanaged.append(Unmanaged(kind, label, okta_id, reason))

    # Groups
    for g in _sorted(inv.get("groups", []), lambda o: o["profile"]["name"]):
        name = g["profile"]["name"]
        if g.get("type") == "OKTA_GROUP":
            add("okta_group", name, g["id"])
        elif g.get("type") == "BUILT_IN":
            skip("group", name, g["id"], "Built-in group (Everyone). Reference it with data \"okta_group\".")
        else:
            skip("group", name, g["id"], "Mastered by a directory or app (APP_GROUP). The sync owns it; reference with a data source.")

    for rule in _sorted(inv.get("group_rules", []), lambda o: o["name"]):
        add("okta_group_rule", rule["name"], rule["id"])

    # Apps
    for app in _sorted(inv.get("apps", []), lambda o: o["label"]):
        label, mode = app["label"], app.get("signOnMode")
        if app.get("name") in FIRST_PARTY_APPS:
            skip("app", label, app["id"], "Okta first-party app.")
            continue
        resource = APP_TYPES.get(mode)
        if app.get("name") == "template_swa3field":
            resource = "okta_app_three_field"
        if not resource:
            skip("app", label, app["id"], f"Sign-on mode {mode} has no matching provider resource.")
            continue
        tf_name = add(resource, label, app["id"])
        if app.get("_group_count", 0) > 0:
            add("okta_app_group_assignments", f"{label} (group assignments)", app["id"], name_text=tf_name)
        if app.get("_user_count", 0) > 0:
            skip("app assignment", label, app["id"],
                 f"{app['_user_count']} direct user assignment(s). Move them to a group before codifying; per-user assignments do not belong in code.")

    # Network zones
    for z in _sorted(inv.get("zones", []), lambda o: o["name"]):
        if z.get("system"):
            skip("network zone", z["name"], z["id"], "System zone. Cannot be deleted; edit in console or import with prevent_destroy if it must be in code.")
        else:
            add("okta_network_zone", z["name"], z["id"])

    # Policies and their rules
    for ptype, policies in sorted(inv.get("policies", {}).items()):
        if ptype not in POLICY_TYPES:
            for p in policies:
                skip("policy", p["name"], p["id"], f"Policy type {ptype} not handled by this tool.")
            continue
        p_res, rule_res, default_res = POLICY_TYPES[ptype]
        for p in _sorted(policies, lambda o: o["name"]):
            if p.get("system"):
                if default_res:
                    add(default_res, p["name"], p["id"], import_id=".")
                else:
                    skip("policy", p["name"], p["id"], f"Default {ptype} policy. No resource can own it; manage its rules only.")
                p_name = slug(p["name"])
            else:
                p_name = add(p_res, p["name"], p["id"])
            for rule in _sorted(p.get("_rules", []), lambda o: o["name"]):
                if rule.get("system"):
                    skip("policy rule", f'{p["name"]} / {rule["name"]}', rule["id"],
                         "System (catch-all) rule. Edit in console; it cannot be created or deleted.")
                else:
                    add(rule_res, f'{p["name"]} / {rule["name"]}', rule["id"],
                        import_id=f'{p["id"]}/{rule["id"]}', name_text=f'{p_name}__{rule["name"]}')

    # Authorization servers
    for a in _sorted(inv.get("auth_servers", []), lambda o: o["name"]):
        if a["id"] == "default":
            a_name = add("okta_auth_server_default", a["name"], a["id"])
        else:
            a_name = add("okta_auth_server", a["name"], a["id"])
        for s in _sorted(a.get("_scopes", []), lambda o: o["name"]):
            if not s.get("system"):
                add("okta_auth_server_scope", f'{a["name"]} / {s["name"]}', s["id"],
                    import_id=f'{a["id"]}/{s["id"]}', name_text=f'{a_name}__{s["name"]}')
        for c in _sorted(a.get("_claims", []), lambda o: o["name"]):
            if not c.get("system"):
                add("okta_auth_server_claim", f'{a["name"]} / {c["name"]}', c["id"],
                    import_id=f'{a["id"]}/{c["id"]}', name_text=f'{a_name}__{c["name"]}_{c.get("claimType", "").lower()}')
        for p in _sorted(a.get("_policies", []), lambda o: o["name"]):
            p_name = add("okta_auth_server_policy", f'{a["name"]} / {p["name"]}', p["id"],
                         import_id=f'{a["id"]}/{p["id"]}', name_text=f'{a_name}__{p["name"]}')
            for rule in _sorted(p.get("_rules", []), lambda o: o["name"]):
                if rule.get("system"):
                    continue
                add("okta_auth_server_policy_rule", f'{a["name"]} / {p["name"]} / {rule["name"]}', rule["id"],
                    import_id=f'{a["id"]}/{p["id"]}/{rule["id"]}', name_text=f'{p_name}__{rule["name"]}')

    # Identity providers
    for idp in _sorted(inv.get("idps", []), lambda o: o["name"]):
        itype = idp.get("type")
        if itype in IDP_TYPES:
            idp_name = add(IDP_TYPES[itype], idp["name"], idp["id"])
            kid = (((idp.get("protocol") or {}).get("credentials") or {}).get("trust") or {}).get("kid")
            if itype == "SAML2" and kid:
                add("okta_idp_saml_key", f'{idp["name"]} signing key', kid, name_text=idp_name)
        elif itype in SOCIAL_IDPS:
            add("okta_idp_social", idp["name"], idp["id"])
        else:
            skip("identity provider", idp["name"], idp["id"], f"IdP type {itype} not handled.")

    for err in inv.get("_errors", []):
        skip(err["kind"], err["what"], "-", err["reason"])

    return r


def render_imports(result: Result, source: str) -> str:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    out = [
        f"# Generated by tools/okta_discover.py from {source} at {stamp}.",
        "# Review, then: terraform plan -generate-config-out=generated.tf",
        "# Delete this file once every import is applied.",
        "",
    ]
    for i in result.imports:
        out += [f"# {i.label}", "import {", f"  to = {i.resource}.{i.name}", f'  id = "{i.id}"', "}", ""]
    return "\n".join(out)


def render_unmanaged(result: Result, source: str) -> str:
    out = [f"# Objects not imported from {source}", "",
           "Each needs an owner decision: leave in the console, reference with a data source, or fix first.", "",
           "| Kind | Name | ID | Reason |", "|---|---|---|---|"]
    for u in sorted(result.unmanaged, key=lambda u: (u.kind, u.label)):
        label = u.label.replace("|", "\\|")
        out.append(f"| {u.kind} | {label} | `{u.id}` | {u.reason} |")
    return "\n".join(out) + "\n"


def fetch_inventory(client) -> dict:
    """Read everything build() needs. GET only."""
    inv: dict = {
        "groups": list(client.list("/api/v1/groups", {"limit": 200})),
        "group_rules": list(client.list("/api/v1/groups/rules", {"limit": 200})),
        "apps": [],
        "zones": list(client.list("/api/v1/zones")),
        "policies": {},
        "auth_servers": [],
        "idps": list(client.list("/api/v1/idps")),
    }
    for app in client.list("/api/v1/apps", {"limit": 200}):
        app["_group_count"] = sum(1 for _ in client.list(f'/api/v1/apps/{app["id"]}/groups', {"limit": 200}))
        users = client.list(f'/api/v1/apps/{app["id"]}/users', {"limit": 500})
        app["_user_count"] = sum(1 for u in users if u.get("scope") == "USER")
        inv["apps"].append(app)
    for ptype in POLICY_TYPES:
        policies = list(client.list("/api/v1/policies", {"type": ptype}))
        for p in policies:
            p["_rules"] = list(client.list(f'/api/v1/policies/{p["id"]}/rules'))
        inv["policies"][ptype] = policies
    inv["_errors"] = []
    try:
        servers = list(client.list("/api/v1/authorizationServers"))
    except requests.HTTPError as exc:
        # 401/403 when the org has no API Access Management, or the scope is missing.
        servers = []
        inv["_errors"].append({"kind": "authorization servers", "what": "all",
                               "reason": f"Not readable ({exc.response.status_code}). No API Access Management, or missing okta.authorizationServers.read."})
    for a in servers:
        base = f'/api/v1/authorizationServers/{a["id"]}'
        a["_scopes"] = list(client.list(f"{base}/scopes"))
        a["_claims"] = list(client.list(f"{base}/claims"))
        a["_policies"] = list(client.list(f"{base}/policies"))
        for p in a["_policies"]:
            p["_rules"] = list(client.list(f'{base}/policies/{p["id"]}/rules'))
        inv["auth_servers"].append(a)
    return inv


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=".", help="Directory for imports.tf and unmanaged.md")
    ap.add_argument("--from-json", help="Use a saved inventory instead of calling Okta")
    ap.add_argument("--save-json", help="Also save the inventory here (secret values redacted; still org config, keep it private)")
    args = ap.parse_args(argv)

    if args.from_json:
        inv = json.loads(Path(args.from_json).read_text())
        source = Path(args.from_json).name
    else:
        from okta_client import OktaClient, org_url
        inv = fetch_inventory(OktaClient())
        source = org_url()
        if args.save_json:
            Path(args.save_json).write_text(json.dumps(redact(inv), indent=2))

    result = build(inv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "imports.tf").write_text(render_imports(result, source))
    (out / "unmanaged.md").write_text(render_unmanaged(result, source))

    by_type: dict[str, int] = {}
    for i in result.imports:
        by_type[i.resource] = by_type.get(i.resource, 0) + 1
    for k in sorted(by_type):
        print(f"{by_type[k]:5d}  {k}")
    print(f"{len(result.imports):5d}  import blocks -> {out / 'imports.tf'}")
    print(f"{len(result.unmanaged):5d}  not imported  -> {out / 'unmanaged.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
