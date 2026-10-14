import json

import gws_groups_inventory as inv

GROUPS = [
    {"id": "1", "email": "eng@corp.com", "name": "Engineering"},
    {"id": "2", "email": "backend@corp.com", "name": "Backend"},
    {"id": "3", "email": "empty@corp.com", "name": "Empty"},
    {"id": "4", "email": "all@corp.com", "name": "Everyone", "adminCreated": True},
    {"id": "5", "email": "loop@corp.com", "name": "Loop", "adminCreated": False},
]

MEMBERS = {
    "eng@corp.com": [
        {"email": "a@corp.com", "type": "USER", "role": "OWNER"},
        {"email": "backend@corp.com", "type": "GROUP", "role": "MEMBER"},
    ],
    "backend@corp.com": [
        {"email": "b@corp.com", "type": "USER", "role": "MEMBER"},
        {"email": "vendor@agency.io", "type": "USER", "role": "MEMBER"},
        {"email": "loop@corp.com", "type": "GROUP", "role": "MEMBER"},
    ],
    "loop@corp.com": [
        {"email": "eng@corp.com", "type": "GROUP", "role": "MEMBER"},  # cycle
    ],
    "empty@corp.com": [],
    "all@corp.com": [{"id": "C01", "type": "CUSTOMER", "role": "MEMBER"}],
}


def rows():
    return {r["email"]: r for r in inv.summarize(GROUPS, MEMBERS, ["corp.com"])["rows"]}


def test_nesting_depth_handles_cycles():
    assert inv.nesting_depth("eng@corp.com", MEMBERS) == 3
    assert inv.nesting_depth("empty@corp.com", MEMBERS) == 0


def test_rows():
    r = rows()
    assert r["backend@corp.com"]["external_users"] == 1
    assert r["eng@corp.com"]["nested_groups"] == 1
    assert r["all@corp.com"]["whole_domain"] is True
    assert r["eng@corp.com"]["owners"] == 1


def test_totals():
    t = inv.summarize(GROUPS, MEMBERS, ["corp.com"])["totals"]
    assert t["groups"] == 5
    assert t["empty"] == 1          # whole-domain group is not empty
    assert t["with_external_users"] == 1
    assert t["nested"] == 3
    assert t["no_owner"] == 4
    assert t["user_created"] == 1
    assert t["max_depth"] == 3


def test_no_domains_means_no_external_flag():
    t = inv.summarize(GROUPS, MEMBERS, [])["totals"]
    assert t.get("with_external_users", 0) == 0


def test_main_from_snapshot(tmp_path):
    snap = tmp_path / "snap.json"
    snap.write_text(json.dumps({"groups": GROUPS, "members": MEMBERS}))
    out = tmp_path / "out"
    assert inv.main(["--from-json", str(snap), "--domain", "corp.com", "--out", str(out)]) == 0
    assert (out / "groups.csv").read_text().startswith("email,")
    assert "vendor@agency.io" in (out / "memberships.csv").read_text()
    assert "backend@corp.com" in (out / "report.md").read_text()
