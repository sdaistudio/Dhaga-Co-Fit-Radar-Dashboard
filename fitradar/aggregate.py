"""Step 5 (code): rates, medians and flags. No model is involved in any number here."""
from collections import Counter
from statistics import median
import pandas as pd
import config
from .ingest import SIZE_ORDER
from .schemas import FIT_REASONS

DIRECTION_WORDS = {"fit_small": "Runs small", "fit_large": "Runs large", "fit_short": "Shorter than shown",
                   "fit_long": "Longer than expected", "fit_other": "Fit is off"}
AREA_WORDS = {"bust": " at the bust", "waist": " at the waist", "hip": " at the hip", "shoulder": " at the shoulder",
              "sleeve": " in the sleeve", "length": "", "overall": "", "not_applicable": ""}
DEFAULT_FIX = {
    "fit_small": "Move the size chart measurements one size down, or add \"order one size up\" to the listing.",
    "fit_large": "Relabel the size chart one size up, or add \"order one size down\" to the listing.",
    "fit_short": "Add garment length in cm to the listing and show the item on a taller model.",
    "fit_long": "Add garment length in cm to the listing.",
    "fit_other": "Review the cut with the vendor before the next order.",
}


def _fit_reason(row):
    if row["reason"] in FIT_REASONS:
        return row["reason"]
    if row.get("second_reason") in FIT_REASONS:
        return row["second_reason"]
    return None


def _pct(x):
    return int(round(x * 100))


def build_groups(results: list[dict], units: pd.DataFrame) -> list[dict]:
    df = pd.DataFrame(results)
    df["fit_reason"] = df.apply(_fit_reason, axis=1)
    counted = df[df["status"] == "accepted"]
    weeks = sorted(units["week_start"].unique())[-6:]
    groups = []
    for (vendor, category), part in df.groupby(["vendor_id", "category"]):
        fit = counted[(counted["vendor_id"] == vendor) & (counted["category"] == category) & counted["fit_reason"].notna()]
        u = units[(units["vendor_id"] == vendor) & (units["category"] == category)]
        units_sold = int(u["units_sold"].sum())
        rate = len(fit) / units_sold if units_sold else 0.0
        directions = Counter(fit["fit_reason"])
        top, top_n = directions.most_common(1)[0] if directions else (None, 0)
        dominant = bool(top) and top_n / len(fit) >= config.DOMINANT_SHARE
        areas = Counter(fit[fit["fit_reason"] == top]["body_area"]) if top else Counter()
        area, area_n = areas.most_common(1)[0] if areas else ("overall", 0)
        area = area if top_n and area_n / top_n >= 0.5 else "overall"
        sizes = [s for s in SIZE_ORDER if s in set(u["size"])]
        by_size = []
        for s in sizes:
            su = int(u[u["size"] == s]["units_sold"].sum())
            by_size.append({"size": s, "rate_pct": _pct((fit["size"] == s).sum() / su) if su else 0})
        trend = []
        for w in weeks:
            wu = int(u[u["week_start"] == w]["units_sold"].sum())
            trend.append(_pct((fit["week_start"] == w).sum() / wu) if wu else 0)
        quotes = (fit[fit["fit_reason"] == top].sort_values("confidence", ascending=False)["text"].drop_duplicates().head(5).tolist()
                  if top else [])
        groups.append({
            "key": f"{vendor}|{category}", "vendor_id": vendor, "category": category, "vendor_city": part["vendor_city"].iloc[0],
            "returns_read": int(len(part)), "fit_returns": int(len(fit)), "units_sold": units_sold,
            "fit_return_rate": rate, "fit_return_rate_pct": _pct(rate),
            "direction": top if dominant else None, "direction_count": int(top_n), "body_area": area,
            "rate_by_size": by_size, "trend_6w": trend, "quotes": quotes,
            "live_skus": int(part["sku_id"].nunique()) if "sku_id" in part else 0,
        })
    # category medians use only vendors with enough returns to trust
    for g in groups:
        peers = [x["fit_return_rate"] for x in groups if x["category"] == g["category"] and x["returns_read"] >= config.MIN_RETURNS]
        med = median(peers) if peers else 0.0
        g["category_median"] = med
        g["category_median_pct"] = _pct(med)
        g["ratio"] = round(g["fit_return_rate"] / med, 1) if med else 0.0
        if g["returns_read"] < config.MIN_RETURNS:
            g["status"], g["signal"] = "too_few", "Too few returns to call"
        elif med and g["fit_return_rate"] >= config.FLAG_RATIO * med and g["direction"]:
            g["status"] = "flag"
            g["signal"] = DIRECTION_WORDS[g["direction"]] + AREA_WORDS.get(g["body_area"], "")
        elif med and g["fit_return_rate"] > med * 1.05:
            g["status"] = "watch"
            g["signal"] = (DIRECTION_WORDS[g["direction"]] + AREA_WORDS.get(g["body_area"], "")) if g["direction"] else "Mixed: no clear direction"
        else:
            g["status"], g["signal"] = "ok", "Close to the category median"
        g["default_fix"] = DEFAULT_FIX.get(g["direction"], "No change yet. Watch for two more weeks before acting.")
        t = g["trend_6w"]
        g["trend_text"] = ("" if not t else f"Rising: {t[0]}% to {t[-1]}%" if t[-1] - t[0] >= 3
                           else f"Falling: {t[0]}% to {t[-1]}%" if t[0] - t[-1] >= 3 else f"Steady at about {round(sum(t) / len(t))}%")
    order = {"flag": 0, "watch": 1, "ok": 2, "too_few": 3}
    return sorted(groups, key=lambda g: (order[g["status"]], -g["fit_return_rate"]))


def evidence_for(g: dict) -> dict:
    """Exactly what the strong model is allowed to see when writing a finding."""
    keep = ["vendor_id", "category", "vendor_city", "returns_read", "fit_returns", "units_sold", "fit_return_rate_pct",
            "category_median_pct", "ratio", "direction", "direction_count", "body_area", "rate_by_size", "trend_6w",
            "quotes", "signal", "status", "default_fix"]
    return {k: g[k] for k in keep}
