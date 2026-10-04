"""Approvals, notes, and the "Mark as fixed" follow-up date. Storage goes to a temporary folder."""
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
import config
from fitradar import store

KEY = "V-03|Kids tees"


@pytest.fixture(autouse=True)
def temp_runs(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RUNS_DIR", tmp_path)
    monkeypatch.setattr(config, "FOLLOW_UP_DAYS", 28)


def test_approve_keeps_the_edited_fix_and_the_note():
    a = store.set_action(KEY, "ok", "  Relabel the chart one size up.  ", "V-03 Kids tees", "  Checked with the vendor  ")
    assert a[KEY]["fix"] == "Relabel the chart one size up."
    assert a[KEY]["note"] == "Checked with the vendor"
    assert a[KEY]["decision"] == "ok"
    assert store.actions()[KEY]["note"] == "Checked with the vendor"


def test_send_back_keeps_the_reason():
    a = store.set_action(KEY, "back", "", "V-03 Kids tees", "Vendor already changed this chart")
    assert a[KEY]["decision"] == "back" and a[KEY]["note"] == "Vendor already changed this chart"


def test_mark_fixed_sets_the_date_and_result_due_four_weeks_later():
    store.set_action(KEY, "ok", "fix", "V-03 Kids tees")
    a = store.set_fixed(KEY, True)[KEY]
    fixed_on = date.fromisoformat(a["fixed_on"])
    assert date.fromisoformat(a["result_due"]) == fixed_on + timedelta(days=28)


def test_result_due_follows_the_setting():
    store.set_action(KEY, "ok", "fix", "V-03 Kids tees")
    config.FOLLOW_UP_DAYS = 14
    a = store.set_fixed(KEY, True)[KEY]
    assert date.fromisoformat(a["result_due"]) - date.fromisoformat(a["fixed_on"]) == timedelta(days=14)


def test_undo_mark_fixed_clears_both_dates_but_keeps_the_approval():
    store.set_action(KEY, "ok", "fix", "V-03 Kids tees")
    store.set_fixed(KEY, True)
    a = store.set_fixed(KEY, False)[KEY]
    assert "fixed_on" not in a and "result_due" not in a and a["decision"] == "ok"


def test_cannot_mark_fixed_before_approval_or_after_send_back():
    with pytest.raises(ValueError):
        store.set_fixed(KEY, True)
    store.set_action(KEY, "back", "", "V-03 Kids tees", "no")
    with pytest.raises(ValueError):
        store.set_fixed(KEY, True)


def test_undoing_the_approval_removes_the_fixed_state_too():
    store.set_action(KEY, "ok", "fix", "V-03 Kids tees")
    store.set_fixed(KEY, True)
    store.set_action(KEY, None)
    assert KEY not in store.actions()


def test_api_round_trip_and_the_message_when_not_approved():
    import server
    client = TestClient(server.app)
    assert client.post("/api/fixed", json={"key": KEY, "fixed": True}).status_code == 409
    assert client.post("/api/action", json={"key": KEY, "decision": "ok", "fix": "Edited fix", "label": "V-03 Kids tees", "note": "ok"}).status_code == 200
    body = client.post("/api/fixed", json={"key": KEY, "fixed": True}).json()
    assert body[KEY]["fix"] == "Edited fix" and body[KEY]["note"] == "ok" and body[KEY]["result_due"]
    assert client.get("/api/state").json()["follow_up_days"] == 28
