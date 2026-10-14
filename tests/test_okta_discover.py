import json
import re
from pathlib import Path

import okta_discover as d
from okta_client import next_link

FIXTURE = Path(__file__).parent / "fixtures" / "okta_inventory.json"


def result():
    return d.build(json.loads(FIXTURE.read_text()))


def imports_by(res, resource):
    return {i.name: i.id for i in res.imports if i.resource == resource}


def unmanaged_ids(res):
    return {u.id for u in res.unmanaged}


def test_slug():
    assert d.slug("Jira Cloud (Prod)") == "jira_cloud_prod"
    assert d.slug("2024 Interns") == "x_2024_interns"
    assert d.slug("***") == "unnamed"


def test_namer_is_stable_and_unique():
    n = d.Namer()
    assert n.name("okta_group", "Eng", "00gAAAAAA111111") == "eng"
    assert n.name("okta_group", "eng", "00gBBBBBB222222") == "eng_222222"
    assert n.name("okta_app_saml", "eng", "0oa1") == "eng"  # separate namespace per type


def test_groups():
    res = result()
    groups = imports_by(res, "okta_group")
    assert set(groups.values()) == {"00g000000000002", "00g000000000003", "00g000000000005"}
    assert "x_2024_interns" in groups
    assert {"00g000000000001", "00g000000000004"} <= unmanaged_ids(res)


def test_apps_and_assignments():
    res = result()
    assert imports_by(res, "okta_app_saml") == {"jira": "0oa000000000002"}
    assert imports_by(res, "okta_app_oauth") == {"jira": "0oa000000000003"}
    assign = imports_by(res, "okta_app_group_assignments")
    # Same label on two app types must not produce duplicate addresses.
    assert sorted(assign.values()) == ["0oa000000000002", "0oa000000000003"]
    assert len(assign) == 2
    # Bookmark with no groups: app imported, no assignment block.
    assert imports_by(res, "okta_app_bookmark") == {"handbook": "0oa000000000005"}
    unmanaged = unmanaged_ids(res)
    assert "0oa000000000001" in unmanaged  # first-party
    assert "0oa000000000004" in unmanaged  # WS-Fed
    reasons = [u.reason for u in res.unmanaged if u.id == "0oa000000000003"]
    assert reasons and "direct user assignment" in reasons[0]


def test_zones():
    res = result()
    assert imports_by(res, "okta_network_zone") == {"office": "nzo000000000002"}
    assert "nzo000000000001" in unmanaged_ids(res)


def test_policies():
    res = result()
    assert list(imports_by(res, "okta_policy_password_default").values()) == ["."]
    assert imports_by(res, "okta_app_signon_policy") == {"any_two_factors": "rst000000000001"}
    rules = imports_by(res, "okta_app_signon_policy_rule")
    assert rules == {"any_two_factors_office_2fa": "rst000000000001/rul000000000002"}
    assert "rul000000000001" in unmanaged_ids(res)  # catch-all
    assert "0pr000000000010" in unmanaged_ids(res)  # default password rule
    # Default sign-on policy is not importable, its custom rule is.
    assert "00p000000000002" in unmanaged_ids(res)
    assert list(imports_by(res, "okta_policy_rule_signon").values()) == ["00p000000000002/0pr000000000020"]


def test_auth_servers():
    res = result()
    assert imports_by(res, "okta_auth_server_default") == {"default": "default"}
    assert imports_by(res, "okta_auth_server") == {"payments_api": "aus000000000001"}
    assert list(imports_by(res, "okta_auth_server_scope").values()) == ["aus000000000001/scp3"]
    assert list(imports_by(res, "okta_auth_server_claim").values()) == ["aus000000000001/ocl1"]
    assert list(imports_by(res, "okta_auth_server_policy").values()) == ["aus000000000001/00p000000000003"]
    assert list(imports_by(res, "okta_auth_server_policy_rule").values()) == ["aus000000000001/00p000000000003/0pr000000000030"]


def test_idps():
    res = result()
    assert imports_by(res, "okta_idp_saml") == {"partner_saml": "0oa000000000101"}
    assert imports_by(res, "okta_idp_saml_key") == {"partner_saml": "key000000000001"}
    assert imports_by(res, "okta_idp_social") == {"google": "0oa000000000102"}
    assert "0oa000000000103" in unmanaged_ids(res)


def test_every_address_unique_and_valid():
    res = result()
    addrs = [f"{i.resource}.{i.name}" for i in res.imports]
    assert len(addrs) == len(set(addrs))
    for a in addrs:
        assert re.fullmatch(r"okta_[a-z0-9_]+\.[a-z_][a-z0-9_]*", a), a


def test_render_and_main(tmp_path):
    rc = d.main(["--from-json", str(FIXTURE), "--out", str(tmp_path)])
    assert rc == 0
    tf = (tmp_path / "imports.tf").read_text()
    assert tf.count("import {") == len(result().imports)
    assert 'to = okta_app_saml.jira' in tf and 'id = "0oa000000000002"' in tf
    md = (tmp_path / "unmanaged.md").read_text()
    assert "| app | Legacy SharePoint |" in md


def test_next_link():
    header = ('<https://x.okta.com/api/v1/groups?limit=2>; rel="self", '
              '<https://x.okta.com/api/v1/groups?after=00g2&limit=2>; rel="next"')
    assert next_link(header) == "https://x.okta.com/api/v1/groups?after=00g2&limit=2"
    assert next_link('<https://x.okta.com/api/v1/groups>; rel="self"') is None
    assert next_link(None) is None


def test_redact_removes_secrets_keeps_kid():
    app = {"credentials": {"oauthClient": {"client_id": "abc", "client_secret": "s3cr3t"}},
           "protocol": {"credentials": {"trust": {"kid": "k1"}, "client": {"client_secret": "x"}}}}
    out = d.redact(app)
    assert out["credentials"]["oauthClient"] == {"client_id": "abc", "client_secret": "<redacted>"}
    assert out["protocol"]["credentials"]["trust"]["kid"] == "k1"
    assert "s3cr3t" not in json.dumps(out) and '"x"' not in json.dumps(out)


def test_three_field_app_and_errors():
    inv = {"apps": [{"id": "0oa9", "name": "template_swa3field", "label": "VPN portal",
                     "signOnMode": "BROWSER_PLUGIN", "_group_count": 0}],
           "_errors": [{"kind": "authorization servers", "what": "all", "reason": "Not readable (403)."}]}
    res = d.build(inv)
    assert imports_by(res, "okta_app_three_field") == {"vpn_portal": "0oa9"}
    assert any(u.kind == "authorization servers" for u in res.unmanaged)


def test_client_refuses_other_origin():
    import pytest
    from okta_client import OktaClient
    c = OktaClient(base_url="https://acme.okta.com")
    for bad in ("http://acme.okta.com/api/v1/groups", "https://evil.example/api/v1/groups"):
        with pytest.raises(ValueError):
            c._check_same_origin(bad)
    c._check_same_origin("https://acme.okta.com/api/v1/groups?after=1")
