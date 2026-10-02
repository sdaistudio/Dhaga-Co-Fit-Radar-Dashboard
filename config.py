"""All settings in one place. Change values here or through environment variables."""
import os
from pathlib import Path

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
RUNS_DIR = Path(os.getenv("FITRADAR_RUNS_DIR", ROOT / "runs"))
WEB_DIR = ROOT / "web"
PROMPTS_DIR = ROOT / "prompts"

# ---- Which reader to use -------------------------------------------------
# "anthropic" : Claude Haiku (fast) + Claude Sonnet (strong)
# "openai"    : GPT fast + GPT strong (model names set below)
# "offline"   : keyword rules, no model call, no cost. For demos without a key.
# "auto"      : anthropic if ANTHROPIC_API_KEY is set, else openai if OPENAI_API_KEY is set, else offline
PROVIDER = os.getenv("FITRADAR_PROVIDER", "auto").lower()

MODELS = {
    "anthropic": {
        "fast": os.getenv("ANTHROPIC_FAST_MODEL", "claude-haiku-4-5-20251001"),
        "strong": os.getenv("ANTHROPIC_STRONG_MODEL", "claude-sonnet-5-5"),
    },
    "openai": {
        # Set these to the GPT models you choose. See docs/MODEL_OPTIONS.md.
        "fast": os.getenv("OPENAI_FAST_MODEL", ""),
        "strong": os.getenv("OPENAI_STRONG_MODEL", ""),
    },
}

# US dollars per million tokens: (input, output). Check the provider's pricing page before the demo.
PRICES = {
    "anthropic": {"fast": (1.00, 5.00), "strong": (2.00, 10.00)},
    "openai": {
        "fast": (float(os.getenv("OPENAI_FAST_PRICE_IN", 0)), float(os.getenv("OPENAI_FAST_PRICE_OUT", 0))),
        "strong": (float(os.getenv("OPENAI_STRONG_PRICE_IN", 0)), float(os.getenv("OPENAI_STRONG_PRICE_OUT", 0))),
    },
    "offline": {"fast": (0.0, 0.0), "strong": (0.0, 0.0)},
}
USD_TO_INR = float(os.getenv("USD_TO_INR", 88))

# ---- Temperatures --------------------------------------------------------
TEMP_READ = 0.0       # reading and re-reading comments
TEMP_EVALUATE = 0.0   # checking a finding
TEMP_FINDING = 0.3    # writing internal prose for Neha's team

# ---- Pipeline thresholds -------------------------------------------------
BATCH_SIZE = 20          # comments per fast-model call
MAX_CONCURRENCY = 8      # batches in flight at once
CONF_ACCEPT = 0.70       # below this a reading is re-read, then queued
MIN_RETURNS = 30         # fewer returns than this: "too few to call"
FLAG_RATIO = 1.5         # fit-return rate at or above this multiple of the category median: flag
DOMINANT_SHARE = 0.60    # one direction must hold this share of fit comments to be "the" direction
MIN_WORDS = 3            # shorter comments are unreadable by rule, not sent to a model
MAX_REWRITES = 1         # a finding that fails its check is rewritten this many times
WEEKLY_COMMENTS = 11804  # client weekly volume used for the cost projection (see docs)


def resolve_provider() -> str:
    if PROVIDER != "auto":
        return PROVIDER
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.getenv("OPENAI_API_KEY") and MODELS["openai"]["fast"]:
        return "openai"
    return "offline"
