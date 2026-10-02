from fitradar.findings import code_check
from fitradar.schemas import Finding

EVIDENCE = {"vendor_id": "V-07", "category": "Kurtis", "returns_read": 212, "fit_returns": 172, "fit_return_rate_pct": 19,
            "category_median_pct": 9, "rate_by_size": [{"size": "XL", "rate_pct": 29}], "quotes": ["size chota hai"]}


def test_finding_using_only_given_numbers_passes():
    f = Finding(headline="Kurtis from V-07 run small.", evidence="172 of 212 returns are about fit; the rate is 19% against 9%.", suggested_fix="Move the chart one size down.")
    assert code_check(f, EVIDENCE) == []


def test_finding_with_an_invented_number_fails():
    f = Finding(headline="Kurtis from V-07 run small.", evidence="85% of returns are about fit.", suggested_fix="Fix the chart.")
    assert any("85" in p for p in code_check(f, EVIDENCE))


def test_finding_must_name_the_vendor():
    f = Finding(headline="Kurtis run small.", evidence="172 of 212 returns.", suggested_fix="Fix the chart.")
    assert code_check(f, EVIDENCE)
