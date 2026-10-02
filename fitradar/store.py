"""The run store: plain JSON files, no database.

runs/latest/run.json    the last finished run (comments, groups, findings, counts, cost)
runs/tags.json          human tags from the review queue   {comment_id: tag}
runs/actions.json       approvals and send-backs           {group_key: {decision, when, fix}}

If runs/latest does not exist, the committed demo run in data/demo_run is shown instead.
"""
import json
from datetime import datetime, timezone
import config

DEMO = config.DATA_DIR / "demo_run" / "run.json"


def _read(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def save_run(run: dict, demo=False):
    _write(DEMO if demo else config.RUNS_DIR / "latest" / "run.json", run)


def load_run() -> dict | None:
    return _read(config.RUNS_DIR / "latest" / "run.json", None) or _read(DEMO, None)


def tags() -> dict:
    return _read(config.RUNS_DIR / "tags.json", {})


def set_tag(comment_id: str, tag: str | None):
    t = tags()
    t.pop(comment_id, None) if tag is None else t.__setitem__(comment_id, tag)
    _write(config.RUNS_DIR / "tags.json", t)
    return t


def actions() -> dict:
    return _read(config.RUNS_DIR / "actions.json", {})


def set_action(key: str, decision: str | None, fix: str = "", label: str = ""):
    a = actions()
    if decision is None:
        a.pop(key, None)
    else:
        a[key] = {"decision": decision, "fix": fix, "label": label, "when": datetime.now(timezone.utc).strftime("%Y-%m-%d")}
    _write(config.RUNS_DIR / "actions.json", a)
    return a
