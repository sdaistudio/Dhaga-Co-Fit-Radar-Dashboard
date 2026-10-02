"""Step 5 on a small fixed table, so the flagging rule can be checked without any model call."""
import pandas as pd
import config
from fitradar import aggregate

WEEK = "2026-09-28"


def _rows(vendor, n, reason="fit_small", status="accepted", second=None, area="bust", text="size chota hai"):
    return [{"comment_id": f"{vendor}-{reason}-{status}-{i}", "vendor_id": vendor, "vendor_city": "Tiruppur", "category": "Kurtis",
             "status": status, "reason": reason, "second_reason": second, "body_area": area, "size": "M", "week_start": WEEK,
             "confidence": 0.9 - i / 1000, "text": f"{text} {i % 3}", "sku_id": f"SKU-{vendor}"} for i in range(n)]


def _units(vendors, sold=100):
    return pd.DataFrame([{"vendor_id": v, "category": "Kurtis", "size": "M", "week_start": WEEK, "units_sold": sold} for v in vendors])


def _groups():
    results = (
        _rows("V-A", 30) + _rows("V-A", 10, reason="quality", area="not_applicable")              # 30 fit of 100 sold: 0.30
        + _rows("V-B", 10) + _rows("V-B", 30, reason="late", area="not_applicable")               # 0.10
        + _rows("V-B", 3, status="queued")                                                         # queued: not counted as fit
        + _rows("V-C", 10) + _rows("V-C", 30, reason="colour", area="not_applicable")             # 0.10
        + _rows("V-D", 7) + _rows("V-D", 7, reason="fit_large", area="waist")                     # 0.14, split 50/50
        + _rows("V-D", 26, reason="quality", area="not_applicable")
        + _rows("V-E", 5)                                                                          # 5 returns only
    )
    return {g["vendor_id"]: g for g in aggregate.build_groups(results, _units(["V-A", "V-B", "V-C", "V-D", "V-E"]))}


def test_rate_is_fit_returns_over_units_sold():
    g = _groups()
    assert g["V-A"]["fit_returns"] == 30 and g["V-A"]["units_sold"] == 100
    assert g["V-A"]["fit_return_rate"] == 0.30 and g["V-A"]["fit_return_rate_pct"] == 30
    assert g["V-A"]["rate_by_size"] == [{"size": "M", "rate_pct": 30}]


def test_queued_comments_are_not_counted_as_fit():
    g = _groups()
    assert g["V-B"]["fit_returns"] == 10 and g["V-B"]["returns_read"] == 43


def test_median_uses_only_vendors_with_enough_returns():
    g = _groups()
    # V-A 0.30, V-B 0.10, V-C 0.10, V-D 0.14. V-E (5 returns) is left out.
    assert round(g["V-A"]["category_median"], 4) == 0.12
    assert round(g["V-E"]["category_median"], 4) == 0.12


def test_statuses():
    g = _groups()
    assert g["V-A"]["status"] == "flag" and g["V-A"]["direction"] == "fit_small" and g["V-A"]["body_area"] == "bust"
    assert g["V-B"]["status"] == g["V-C"]["status"] == "ok"
    assert g["V-D"]["status"] == "watch" and g["V-D"]["direction"] is None
    assert g["V-D"]["signal"] == "Mixed: no clear direction"
    assert g["V-E"]["status"] == "too_few"


def test_flag_needs_the_ratio(monkeypatch):
    monkeypatch.setattr(config, "FLAG_RATIO", 3.0)        # 0.30 is 2.5 times the median: no longer enough
    assert _groups()["V-A"]["status"] == "watch"


def test_too_few_follows_the_threshold(monkeypatch):
    monkeypatch.setattr(config, "MIN_RETURNS", 5)
    assert _groups()["V-E"]["status"] != "too_few"


def test_flagged_come_first_and_quotes_are_distinct():
    groups = aggregate.build_groups(
        _rows("V-A", 30) + _rows("V-A", 10, reason="quality", area="not_applicable") + _rows("V-B", 10)
        + _rows("V-B", 30, reason="late", area="not_applicable") + _rows("V-C", 10) + _rows("V-C", 30, reason="colour"),
        _units(["V-A", "V-B", "V-C"]))
    assert groups[0]["vendor_id"] == "V-A"
    quotes = groups[0]["quotes"]
    assert len(quotes) == len(set(quotes)) == 3 and len(quotes) <= 5


def test_evidence_holds_only_what_the_writer_may_see():
    g = _groups()["V-A"]
    evidence = aggregate.evidence_for(g)
    assert "fit_return_rate" not in evidence and "category_median" not in evidence   # only rounded figures go to the model
    assert evidence["fit_return_rate_pct"] == 30 and evidence["vendor_id"] == "V-A"
