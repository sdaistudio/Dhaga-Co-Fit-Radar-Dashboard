"""The pipeline as a LangGraph state graph.

    load -> read -> [any unclear?] -> reread -> queue -> aggregate -> write -> evaluate -> [failed and rewrites left?] -> write
                          \\________________________^                                             \\-> save -> END

Patterns, and where each sits:
  Parallelization      read       batches of 20 comments run side by side
  Routing              reread     only comments under the confidence threshold, or with two reasons, go to the strong model;
                       queue      what is still unclear goes to a person
  Prompt chaining      read -> aggregate (code) -> write: each step is fed only the output of the one before
  Evaluator-optimizer  write <-> evaluate: a finding that fails its check is rewritten with the reasons, once
"""
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TypedDict
from langgraph.graph import END, StateGraph
import config
from . import aggregate, cost, findings as findings_mod, ingest, store
from .llm import make_reader
from .schemas import FIT_REASONS, REASON_LABEL, reason_group

STEPS = [
    {"n": 1, "title": "Load and clean", "by": "Code", "desc": "Read the files, match each comment to its vendor and size, drop blanks and repeats."},
    {"n": 2, "title": "Read every comment", "by": "Fast", "desc": "Batches of 20 at once: reason, body area, how sure."},
    {"n": 3, "title": "Re-read the unclear ones", "by": "Strong", "desc": "Under 70% sure or two reasons: the stronger model looks again."},
    {"n": 4, "title": "Pass the rest to a person", "by": "Person", "desc": "Still under 70% sure: goes to the review queue."},
    {"n": 5, "title": "Count and compare", "by": "Code", "desc": "Fit-return rate by vendor, category and size, against the category median."},
    {"n": 6, "title": "Write each finding", "by": "Strong", "desc": "From step 5's numbers and quotes only."},
    {"n": 7, "title": "Evaluate each finding", "by": "Fast + code", "desc": "Every figure and claim checked. A failure is rewritten once."},
]
# "Fit" alone is an older tag with no direction; the review queue now offers the four directions.
TAG_TO_REASON = {"Fit: too small": "fit_small", "Fit: too large": "fit_large", "Fit: too short": "fit_short", "Fit: too long": "fit_long",
                 "Fit": "fit_other", "Quality": "quality", "Colour": "colour", "Changed mind": "changed_mind"}


class State(TypedDict, total=False):
    comments_path: str
    units_path: str
    provider: str
    reader: Any
    progress: Callable[[int, str], None]
    comments: Any            # DataFrame
    units: Any               # DataFrame
    report: dict
    results: dict            # comment_id -> result row
    groups: list
    findings: dict           # group key -> finding record
    rewrite_round: int
    step_counts: dict
    step_seconds: dict
    run: dict


def _tick(state: State, step: int, note: str = ""):
    if state.get("progress"):
        state["progress"](step, note)


def _timed(state: State, step: int, started: float):
    seconds = dict(state.get("step_seconds", {})); seconds[str(step)] = round(seconds.get(str(step), 0) + time.time() - started, 2)
    return seconds


def _apply(row: dict, reading, read_by: str):
    row.update({"reason": reading.reason.value, "second_reason": reading.second_reason.value if reading.second_reason else None,
                "body_area": reading.body_area.value, "language": reading.language, "confidence": min(1.0, max(0.0, float(reading.confidence))),
                "evidence_phrase": reading.evidence_phrase, "meaning_en": reading.meaning_en, "read_by": read_by})


# ---- nodes ---------------------------------------------------------------
def load(state: State) -> State:
    _tick(state, 1); started = time.time()
    comments, units, report = ingest.load(Path(state["comments_path"]), Path(state["units_path"]))
    tags = store.tags()
    results = {}
    for r in comments.to_dict("records"):
        row = {"comment_id": r["comment_id"], "text": r["text"], "source": r["source"], "vendor_id": r["vendor_id"],
               "vendor_city": r["vendor_city"], "category": r["category"], "size": r["size"], "week_start": r["week_start"],
               "sku_id": r.get("sku_id", ""), "reason": "unclear", "second_reason": None, "body_area": "not_applicable",
               "language": "", "confidence": 0.0, "evidence_phrase": "", "meaning_en": "", "status": "pending", "read_by": "",
               "path": [{"by": "Code", "note": "Cleaned and matched to its vendor and size"}]}
        if r["unreadable"]:
            row.update(status="unreadable_rule", read_by="Rule, no model")
            row["path"] = [{"by": "Code", "note": "Under 3 words or no letters: marked unreadable"},
                           {"by": "Code", "note": "Not sent to a model, so it costs nothing"}]
        elif r["comment_id"] in tags and tags[r["comment_id"]] in TAG_TO_REASON:
            row.update(status="accepted", read_by="Person", reason=TAG_TO_REASON[tags[r["comment_id"]]], confidence=1.0)
            row["path"].append({"by": "Person", "note": f"Tagged earlier by a person: {tags[r['comment_id']]}"})
        results[r["comment_id"]] = row
    return {"comments": comments, "units": units, "report": report, "results": results,
            "step_counts": {"1": f"{report['in_file']:,} in · {report['dropped_duplicates']} dropped"
                                 + (f" · test run: first {report['limited_to']:,} only" if report["limited_to"] else "")},
            "step_seconds": _timed(state, 1, started), "rewrite_round": 0, "findings": {}}


def read(state: State) -> State:
    _tick(state, 2); started = time.time()
    results = state["results"]
    todo = [{"comment_id": r["comment_id"], "text": r["text"], "category": r["category"], "size_bought": r["size"]}
            for r in results.values() if r["status"] == "pending"]
    batches = [todo[i:i + config.BATCH_SIZE] for i in range(0, len(todo), config.BATCH_SIZE)]
    readings = state["reader"].read_batches(batches)
    for c in todo:
        row = results[c["comment_id"]]
        reading = readings.get(c["comment_id"])
        if reading is None:
            row.update(status="unclear_schema")
            row["path"].append({"by": "Fast", "note": "The reply could not be read automatically"})
            continue
        _apply(row, reading, "Fast model")
        if reading.confidence >= config.CONF_ACCEPT and not reading.second_reason and reading.reason.value != "unclear":
            row["status"] = "accepted"
            row["path"].append({"by": "Fast", "note": f"Read once; {round(reading.confidence * 100)}% sure, so accepted"})
        else:
            row["status"] = "unclear"
            why = "two reasons" if reading.second_reason else f"only {round(reading.confidence * 100)}% sure"
            row["path"].append({"by": "Fast", "note": f"First read: {why}"})
    counts = dict(state["step_counts"]); counts["2"] = f"{len(todo):,} read"
    return {"results": results, "step_counts": counts, "step_seconds": _timed(state, 2, started)}


def needs_reread(state: State) -> str:
    return "reread" if any(r["status"].startswith("unclear") for r in state["results"].values()) else "queue"


def reread(state: State) -> State:
    _tick(state, 3); started = time.time()
    results, n = state["results"], 0
    for row in results.values():
        if not row["status"].startswith("unclear"):
            continue
        n += 1
        comment = {"comment_id": row["comment_id"], "text": row["text"], "category": row["category"], "size_bought": row["size"]}
        reading = state["reader"].reread(comment, None)
        if reading is None:
            row["status"] = "queued"
            row["path"].append({"by": "Strong", "note": "The re-read could not be completed"})
            continue
        _apply(row, reading, "Strong model")
        sure = round(reading.confidence * 100)
        if reading.confidence >= config.CONF_ACCEPT and reading.reason.value != "unclear":
            row["status"] = "accepted"
            both = " Both reasons tagged." if reading.second_reason else ""
            row["path"].append({"by": "Strong", "note": f"Re-read; {sure}% sure, so accepted.{both}"})
        else:
            row["status"] = "queued"
            row["path"].append({"by": "Strong", "note": f"Re-read; still only {sure}% sure"})
        if n % 10 == 0:
            _tick(state, 3, f"{n} re-read")
    counts = dict(state["step_counts"]); counts["3"] = f"{n:,} re-read"
    return {"results": results, "step_counts": counts, "step_seconds": _timed(state, 3, started)}


def queue(state: State) -> State:
    _tick(state, 4); started = time.time()
    n = 0
    for row in state["results"].values():
        if row["status"] in ("queued", "unclear_schema", "unclear"):
            row["status"] = "queued"; row["read_by"] = "Review queue"; n += 1
            row["path"].append({"by": "Person", "note": "Sent to the review queue, not guessed"})
    counts = dict(state["step_counts"]); counts.setdefault("3", "0 re-read"); counts["4"] = f"{n:,} queued"
    return {"results": state["results"], "step_counts": counts, "step_seconds": _timed(state, 4, started)}


def aggregate_node(state: State) -> State:
    _tick(state, 5); started = time.time()
    groups = aggregate.build_groups(list(state["results"].values()), state["units"])
    counts = dict(state["step_counts"]); counts["5"] = f"{len(groups)} vendors"
    return {"groups": groups, "step_counts": counts, "step_seconds": _timed(state, 5, started)}


def write(state: State) -> State:
    _tick(state, 6); started = time.time()
    found = dict(state["findings"])
    for g in state["groups"]:
        if g["status"] not in ("flag", "watch"):
            continue
        previous = found.get(g["key"])
        if previous and previous["check"] != "failed":
            continue                                    # already passed; only failures are rewritten
        evidence = aggregate.evidence_for(g)
        finding = state["reader"].write_finding(evidence, previous["problems"] if previous else None)
        found[g["key"]] = {"finding": finding.model_dump() if finding else None, "check": "pending",
                           "problems": previous["problems"] if previous else [], "attempts": (previous["attempts"] + 1) if previous else 1}
    return {"findings": found, "step_seconds": _timed(state, 6, started)}


def evaluate(state: State) -> State:
    _tick(state, 7); started = time.time()
    found = dict(state["findings"])
    by_key = {g["key"]: g for g in state["groups"]}
    for key, record in found.items():
        if record["check"] != "pending":
            continue
        evidence = aggregate.evidence_for(by_key[key])
        if record["finding"] is None:
            record.update(check="failed", problems=["No finding was produced."])
            continue
        from .schemas import Finding
        finding = Finding(**record["finding"])
        problems = findings_mod.code_check(finding, evidence)            # code: every figure must be in the data
        verdict = state["reader"].evaluate(finding, evidence)            # model: every claim must be supported
        if not verdict.supported:
            problems += verdict.problems or ["The checker did not find the claims supported."]
        record.update(check="failed" if problems else ("rewritten" if record["attempts"] > 1 else "passed"), problems=problems)
    return {"findings": found, "rewrite_round": state["rewrite_round"] + 1, "step_seconds": _timed(state, 7, started)}


def after_evaluate(state: State) -> str:
    failed = any(r["check"] == "failed" for r in state["findings"].values())
    return "write" if failed and state["rewrite_round"] <= config.MAX_REWRITES else "save"


def save(state: State) -> State:
    results, groups, found = state["results"], state["groups"], state["findings"]
    rows = list(results.values())
    read_rows = [r for r in rows if r["status"] != "unreadable_rule"]
    shares = {k: 0 for k in ["fit", "quality", "colour", "late", "other", "person"]}
    for r in rows:
        if r["status"] == "accepted":
            shares["fit" if (r["reason"] in FIT_REASONS or r["second_reason"] in FIT_REASONS) else reason_group(r["reason"])] += 1
        else:
            shares["person"] += 1
    total = max(1, len(rows))
    for g in groups:
        record = found.get(g["key"])
        if record:
            verified = record["check"] in ("passed", "rewritten")
            g["finding"] = record["finding"] if verified else None
            g["check"] = record["check"]; g["problems"] = record["problems"]; g["attempts"] = record["attempts"]
        else:
            g["finding"], g["check"], g["problems"], g["attempts"] = None, "none", [], 0
    for r in rows:
        r["reason_label"] = ("Unreadable" if r["status"] == "unreadable_rule" else "Needs a person" if r["status"] == "queued"
                             else REASON_LABEL.get(r["reason"], r["reason"]) + (" + " + REASON_LABEL[r["second_reason"]].lower() if r["second_reason"] else ""))
        r["group"] = ("person" if r["status"] != "accepted" else "fit" if (r["reason"] in FIT_REASONS or r["second_reason"] in FIT_REASONS)
                      else reason_group(r["reason"]))
    counts = dict(state["step_counts"])
    wrote = [r for r in found.values()]
    counts["6"] = f"{len(wrote)} written"
    counts["7"] = (f"{sum(r['check'] == 'passed' for r in wrote)} passed · {sum(r['check'] == 'rewritten' for r in wrote)} rewritten"
                   + (f" · {sum(r['check'] == 'failed' for r in wrote)} not verified" if any(r["check"] == "failed" for r in wrote) else ""))
    reader = state["reader"]
    run = {
        "run_id": uuid.uuid4().hex[:8], "finished_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "provider": state["provider"], "models": reader.models, "week_of": state["report"]["week_of"],
        "counts": {"in_file": state["report"]["in_file"], "dropped": state["report"]["dropped_duplicates"],
                   "unreadable_rule": state["report"]["unreadable_rule"], "read": len(read_rows),
                   "queued": sum(r["status"] == "queued" for r in rows),
                   "flagged": sum(g["status"] == "flag" for g in groups),
                   "fit_share_pct": round(100 * shares["fit"] / total)},
        "reason_share": {k: round(100 * v / total) for k, v in shares.items()},
        "steps": [dict(s, count=counts.get(str(s["n"]), ""), seconds=state["step_seconds"].get(str(s["n"]), 0)) for s in STEPS],
        "cost": cost.summarise(reader.usage.rows, state["provider"], len(read_rows)),
        "groups": groups, "comments": rows,
    }
    return {"run": run}


def build():
    g = StateGraph(State)
    for name, fn in [("load", load), ("read", read), ("reread", reread), ("queue", queue), ("aggregate", aggregate_node),
                     ("write", write), ("evaluate", evaluate), ("save", save)]:
        g.add_node(name, fn)
    g.set_entry_point("load")
    g.add_edge("load", "read")
    g.add_conditional_edges("read", needs_reread, {"reread": "reread", "queue": "queue"})     # routing
    g.add_edge("reread", "queue")
    g.add_edge("queue", "aggregate")
    g.add_edge("aggregate", "write")
    g.add_edge("write", "evaluate")
    g.add_conditional_edges("evaluate", after_evaluate, {"write": "write", "save": "save"})    # evaluator-optimizer loop
    g.add_edge("save", END)
    return g.compile()


def run_pipeline(provider: str | None = None, progress=None, comments_path=None, units_path=None, as_demo=False) -> dict:
    provider = provider or config.resolve_provider()
    state = build().invoke({
        "comments_path": str(comments_path or config.DATA_DIR / "comments.csv"),
        "units_path": str(units_path or config.DATA_DIR / "units_sold.csv"),
        "provider": provider, "reader": make_reader(provider), "progress": progress,
    })
    store.save_run(state["run"], demo=as_demo)
    return state["run"]


if __name__ == "__main__":
    import sys
    result = run_pipeline(provider=sys.argv[1] if len(sys.argv) > 1 else None, progress=lambda s, n="": print(f"step {s} {n}"),
                          as_demo="--demo" in sys.argv)
    print(result["counts"], result["cost"]["usd"])
