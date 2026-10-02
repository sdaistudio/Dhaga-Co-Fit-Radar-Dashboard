"""Step 1 (code): load the files, tidy them, and decide which comments are worth sending to a model."""
from pathlib import Path
import pandas as pd
import config

# Vendors label sizes differently. One lookup makes them comparable.
SIZE_MAP = {
    "s": "S", "small": "S", "36": "S", "m": "M", "medium": "M", "38": "M", "l": "L", "large": "L", "40": "L",
    "xl": "XL", "x-large": "XL", "xlarge": "XL", "42": "XL",
    "2y": "2Y", "2-3 yrs": "2Y", "age 2": "2Y", "4y": "4Y", "4-5 yrs": "4Y", "age 4": "4Y",
    "6y": "6Y", "6-7 yrs": "6Y", "age 6": "6Y", "8y": "8Y", "8-9 yrs": "8Y", "age 8": "8Y",
}
SIZE_ORDER = ["S", "M", "L", "XL", "2Y", "4Y", "6Y", "8Y"]
COMMENT_COLUMNS = ["comment_id", "source", "text", "order_id", "vendor_id", "vendor_city", "category", "size_bought", "created_at"]
UNITS_COLUMNS = ["vendor_id", "category", "size", "week_start", "units_sold"]


class BadFile(ValueError):
    """Raised with a message the screen can show as it is."""


def normalise_size(value) -> str:
    key = str(value).strip().lower()
    return SIZE_MAP.get(key, str(value).strip().upper())


def unreadable_by_rule(text: str) -> bool:
    text = (text or "").strip()
    if not any(ch.isalpha() for ch in text):
        return True
    return len(text.split()) < config.MIN_WORDS


def _read(path: Path, required: list[str], name: str) -> pd.DataFrame:
    if not Path(path).exists():
        raise BadFile(f"{name} was not found at {path}. Run: python data/generate_synthetic.py")
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise BadFile(f"{name} is missing these columns: {', '.join(missing)}")
    return df


def load(comments_path: Path, units_path: Path):
    comments = _read(comments_path, COMMENT_COLUMNS, "The comments file")
    units = _read(units_path, UNITS_COLUMNS, "The units-sold file")

    in_file = len(comments)
    comments["text"] = comments["text"].astype(str).str.strip()
    comments = comments.drop_duplicates(subset=["order_id", "text"], keep="first").reset_index(drop=True)
    dropped = in_file - len(comments)

    comments["size"] = comments["size_bought"].map(normalise_size)
    created = pd.to_datetime(comments["created_at"], errors="coerce")
    comments["week_start"] = (created - pd.to_timedelta(created.dt.weekday, unit="D")).dt.strftime("%Y-%m-%d")
    comments["unreadable"] = comments["text"].map(unreadable_by_rule)

    units["size"] = units["size"].map(normalise_size)
    units["units_sold"] = pd.to_numeric(units["units_sold"], errors="coerce").fillna(0).astype(int)

    report = {"in_file": in_file, "dropped_duplicates": dropped, "unreadable_rule": int(comments["unreadable"].sum()),
              "to_read": int((~comments["unreadable"]).sum()),
              "week_of": str(comments["week_start"].max())}
    return comments, units, report
