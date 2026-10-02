"""Accuracy test: compare the latest run's readings with the hand labels in data/gold_labels.csv.

Run:  python -m fitradar.accuracy
Agreement is measured on the six groups shown on screen (fit, quality, colour, late, other, needs a person).
A change to a prompt should be kept only if this score rises. Record each version and its score in prompts/CHANGELOG.md.
"""
import csv
from collections import Counter, defaultdict
import config
from . import store
from .schemas import FIT_REASONS, reason_group


def gold_group(reason: str) -> str:
    if reason in FIT_REASONS:
        return "fit"
    if reason in ("unreadable", "unclear"):
        return "person"
    return reason_group(reason)


def score() -> dict:
    run = store.load_run()
    if not run:
        raise SystemExit("No run found. Run the pipeline first.")
    got = {c["comment_id"]: c["group"] for c in run["comments"]}
    with open(config.DATA_DIR / "gold_labels.csv", encoding="utf-8") as f:
        gold = list(csv.DictReader(f))
    per, confusion, right, total = defaultdict(lambda: [0, 0]), Counter(), 0, 0
    for row in gold:
        if row["comment_id"] not in got:
            continue                      # dropped as a duplicate
        want, have = gold_group(row["gold_reason"]), got[row["comment_id"]]
        total += 1; per[want][1] += 1
        if want == have:
            right += 1; per[want][0] += 1
        else:
            confusion[(want, have)] += 1
    return {"provider": run["provider"], "checked": total, "agreement_pct": round(100 * right / total, 1) if total else 0,
            "per_group": {k: {"right": v[0], "of": v[1]} for k, v in sorted(per.items())},
            "misses": [{"expected": a, "got": b, "count": n} for (a, b), n in confusion.most_common()]}


if __name__ == "__main__":
    result = score()
    print(f"Reader: {result['provider']}   Checked: {result['checked']}   Agreement: {result['agreement_pct']}%")
    for group, v in result["per_group"].items():
        print(f"  {group:8} {v['right']:3} of {v['of']:3}")
    for m in result["misses"]:
        print(f"  expected {m['expected']}, got {m['got']}: {m['count']}")
