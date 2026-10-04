"""Cost arithmetic against a hand-worked example. Prices are fixed here so the test checks the sums, not config."""
import pytest
import config
from fitradar import cost


@pytest.fixture(autouse=True)
def fixed_prices(monkeypatch):
    monkeypatch.setitem(config.PRICES, "anthropic", {"fast": (1.00, 5.00), "strong": (2.00, 10.00)})
    monkeypatch.setattr(config, "USD_TO_INR", 88.0)
    monkeypatch.setattr(config, "WEEKLY_COMMENTS", 11804)


ROWS = [
    {"role": "fast", "step": "read", "calls": 100, "input_tokens": 900_000, "output_tokens": 120_000, "seconds": 0.0},
    {"role": "fast", "step": "read_time", "calls": 0, "input_tokens": 0, "output_tokens": 0, "seconds": 40.0},
    {"role": "strong", "step": "reread", "calls": 300, "input_tokens": 100_000, "output_tokens": 20_000, "seconds": 90.0},
    {"role": "strong", "step": "finding", "calls": 5, "input_tokens": 10_000, "output_tokens": 2_000, "seconds": 15.0},
    {"role": "fast", "step": "evaluate", "calls": 5, "input_tokens": 10_000, "output_tokens": 1_000, "seconds": 5.0},
]

# By hand, in dollars:
#   read      0.9 x 1  + 0.12  x 5  = 0.90 + 0.60  = 1.500
#   re-read   0.1 x 2  + 0.02  x 10 = 0.20 + 0.20  = 0.400
#   findings  0.01 x 2 + 0.002 x 10 = 0.02 + 0.02  = 0.040
#   check     0.01 x 1 + 0.001 x 5  = 0.01 + 0.005 = 0.015
#   total                                          = 1.955   (x 88 = Rs 172.04)
#   weekly    1.955 x 11,804 / 2,000 comments      = 11.538  (x 88 = Rs 1,015)


def test_hand_worked_example():
    out = cost.summarise(ROWS, "anthropic", comments_read=2000)
    assert [line["usd"] for line in out["lines"]] == pytest.approx([1.5, 0.4, 0.04, 0.015])
    assert out["usd"] == pytest.approx(1.955)
    assert out["inr"] == pytest.approx(172.04)
    assert out["weekly_usd"] == pytest.approx(11.54)
    assert out["weekly_inr"] == 1015
    assert out["priced"] is True


def test_seconds_include_the_parallel_read_time():
    out = cost.summarise(ROWS, "anthropic", comments_read=2000)
    assert out["lines"][0]["seconds"] == 40.0
    assert out["seconds"] == 150.0


def test_each_line_shows_its_arithmetic():
    line = cost.summarise(ROWS, "anthropic", comments_read=2000)["lines"][0]
    assert line["sum"] == "900,000 in x $1 + 120,000 out x $5, per million"
    assert line["calls"] == 100


def test_offline_costs_nothing_and_says_so():
    out = cost.summarise(ROWS, "offline", comments_read=2000)
    assert out["usd"] == 0 and out["priced"] is False


def test_reported_cost_is_used_instead_of_a_price_guess():
    rows = [{"role": "fast", "step": "read", "calls": 1, "input_tokens": 1000, "output_tokens": 500, "seconds": 0.0, "billed_usd": 0.01},
            {"role": "fast", "step": "read", "calls": 1, "input_tokens": 1000, "output_tokens": 500, "seconds": 0.0, "billed_usd": 0.03}]
    out = cost.summarise(rows, "openrouter", comments_read=40)
    assert out["lines"][0]["usd"] == pytest.approx(0.04)
    assert "billed $0.0400 by the service across 2 calls" in out["lines"][0]["sum"]
    assert out["priced"] is True


def test_partly_reported_cost_falls_back_to_price_times_tokens():
    rows = [{"role": "fast", "step": "read", "calls": 1, "input_tokens": 1_000_000, "output_tokens": 0, "seconds": 0.0, "billed_usd": 0.5},
            {"role": "fast", "step": "read", "calls": 1, "input_tokens": 0, "output_tokens": 0, "seconds": 0.0}]
    out = cost.summarise(rows, "anthropic", comments_read=40)
    assert out["lines"][0]["usd"] == pytest.approx(1.0)       # 1M in x $1, not the 0.5 reported for one call


def test_no_comments_read_means_no_projection():
    assert cost.summarise([], "anthropic", comments_read=0)["weekly_usd"] == 0
