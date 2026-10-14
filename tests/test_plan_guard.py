import json

import plan_guard as g


def rc(address, actions):
    return {"address": address, "type": address.split(".")[-2], "change": {"actions": actions}}


def plan(*changes, drift=()):
    return {"resource_changes": list(changes), "resource_drift": [{"address": a} for a in drift]}


def test_no_changes():
    summary, problems = g.evaluate(plan(rc("okta_group.eng", ["no-op"])))
    assert problems == []
    assert "No changes" in summary


def test_create_and_update_pass():
    summary, problems = g.evaluate(plan(rc("okta_group.new", ["create"]), rc("okta_app_saml.wiki", ["update"])))
    assert problems == []
    assert "**1** to create" in summary and "**1** to update" in summary


def test_delete_of_protected_is_blocked():
    _, problems = g.evaluate(plan(rc("okta_group.eng", ["delete"])))
    assert len(problems) == 1 and "okta_group.eng" in problems[0]


def test_replace_counts_as_destructive():
    summary, problems = g.evaluate(plan(rc("module.x.okta_app_oauth.this", ["delete", "create"])))
    assert problems and "replace" in problems[0]
    assert "| replace |" in summary


def test_allow_destroy_label():
    _, problems = g.evaluate(plan(rc("okta_group.eng", ["delete"])), allow_destroy=True)
    assert problems == []


def test_unprotected_delete_is_fine():
    _, problems = g.evaluate(plan(rc("okta_trusted_origin.old", ["delete"])))
    assert problems == []


def test_expect_no_changes_fails_on_any_change():
    _, problems = g.evaluate(plan(rc("okta_group.eng", ["update"])), expect_no_changes=True)
    assert problems and "Expected no changes" in problems[0]


def test_drift_is_reported():
    summary, _ = g.evaluate(plan(drift=["okta_group.eng"]))
    assert "Changed outside Terraform" in summary and "okta_group.eng" in summary


def test_cli(tmp_path, monkeypatch):
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(plan(rc("okta_network_zone.office", ["delete"]))))
    out = tmp_path / "summary.md"
    monkeypatch.delenv("ALLOW_DESTROY", raising=False)
    assert g.main([str(p), "--summary", str(out)]) == 1
    assert "Blocked" in out.read_text()
    monkeypatch.setenv("ALLOW_DESTROY", "true")
    assert g.main([str(p)]) == 0
    bad = tmp_path / "bad.json"
    bad.write_text("not json")
    assert g.main([str(bad)]) == 2
