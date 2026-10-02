"""Runs the whole LangGraph pipeline with the offline reader on the bundled stand-in data. No API key needed."""
import config
from fitradar import cost
from fitradar.graph import run_pipeline


def test_planted_patterns_are_found(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RUNS_DIR", tmp_path)
    run = run_pipeline(provider="offline")
    status = {g["vendor_id"]: g["status"] for g in run["groups"]}
    assert status["V-07"] == status["V-12"] == status["V-03"] == "flag"
    assert status["V-18"] == "watch"
    assert status["V-21"] == "too_few"
    by = {g["vendor_id"]: g for g in run["groups"]}
    assert by["V-07"]["direction"] == "fit_small" and by["V-07"]["body_area"] == "bust"
    assert by["V-21"]["finding"] is None
    assert run["counts"]["queued"] > 0
    assert sum(run["reason_share"].values()) in range(98, 103)
    assert all(g["check"] in ("passed", "rewritten") for g in run["groups"] if g["status"] in ("flag", "watch"))


def test_cost_arithmetic():
    rows = [{"role": "fast", "step": "read", "calls": 1, "input_tokens": 1_000_000, "output_tokens": 1_000_000, "seconds": 1.0}]
    out = cost.summarise(rows, "anthropic", comments_read=1000)
    assert out["usd"] == 6.0          # 1.00 in + 5.00 out
    assert out["inr"] == 6.0 * config.USD_TO_INR
