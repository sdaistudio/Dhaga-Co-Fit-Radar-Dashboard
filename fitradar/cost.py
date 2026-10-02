"""Cost and time accounting. Arithmetic only: tokens x price."""
import config


def summarise(usage_rows: list[dict], provider: str, comments_read: int) -> dict:
    prices = config.PRICES.get(provider, config.PRICES["offline"])
    lines, total, total_seconds = [], 0.0, 0.0
    labels = [("fast", "read", "Fast model: read comments"), ("strong", "reread", "Strong model: re-read unclear comments"),
              ("strong", "finding", "Strong model: write findings"), ("fast", "evaluate", "Fast model: check findings")]
    for role, step, label in labels:
        rows = [r for r in usage_rows if r["role"] == role and r["step"] == step]
        tin = sum(r["input_tokens"] for r in rows); tout = sum(r["output_tokens"] for r in rows)
        calls = sum(r["calls"] for r in rows); seconds = sum(r["seconds"] for r in rows)
        if step == "read":
            seconds += sum(r["seconds"] for r in usage_rows if r["step"] == "read_time")
        pin, pout = prices[role]
        usd = tin * pin / 1_000_000 + tout * pout / 1_000_000
        total += usd; total_seconds += seconds
        lines.append({"label": label, "calls": calls, "input_tokens": tin, "output_tokens": tout, "seconds": round(seconds, 1),
                      "usd": round(usd, 4), "sum": f"{tin:,} in x ${pin:g} + {tout:,} out x ${pout:g}, per million"})
    priced = any(p > 0 for pair in prices.values() for p in pair)
    weekly = total * config.WEEKLY_COMMENTS / comments_read if comments_read else 0.0
    return {"lines": lines, "usd": round(total, 4), "inr": round(total * config.USD_TO_INR, 2), "seconds": round(total_seconds, 1),
            "weekly_usd": round(weekly, 2), "weekly_inr": round(weekly * config.USD_TO_INR), "weekly_comments": config.WEEKLY_COMMENTS,
            "usd_to_inr": config.USD_TO_INR, "priced": priced}
