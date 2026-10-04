"""The readers. One interface, three ways to fill it:

  ModelReader("anthropic")  Claude Haiku (fast) + Claude Sonnet (strong), through LangChain
  ModelReader("openrouter") Any models through OpenRouter (OpenAI-compatible API), through LangChain
  ModelReader("openai")     GPT fast + GPT strong, through LangChain
  OfflineReader()           keyword rules, no model call. For demos with no API key.

Every model call returns a validated Pydantic record (structured output). Free text is never parsed.
"""
import json
import os
import re
import time
from langchain_core.messages import HumanMessage, SystemMessage
import config
from .schemas import BatchReadings, CommentReading, Evaluation, Finding, FIT_REASONS


def _prompt(name: str) -> str:
    return (config.PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


class ModelError(RuntimeError):
    """The model service could not be used. The message is written for the screen."""


def _describe(error) -> str:
    return f"{type(error).__name__}: {str(error)[:300]}"


class Usage:
    """Token and time log for one run."""
    def __init__(self):
        self.rows = []

    def add(self, role, step, raw=None, seconds=0.0, calls=1):
        meta = getattr(raw, "usage_metadata", None) or {}
        # OpenRouter reports what each call actually cost. Routers bill at the price of whichever model served the call.
        billed = ((getattr(raw, "response_metadata", None) or {}).get("token_usage") or {}).get("cost")
        self.rows.append({"role": role, "step": step, "calls": calls, "input_tokens": int(meta.get("input_tokens", 0)),
                          "output_tokens": int(meta.get("output_tokens", 0)), "seconds": round(seconds, 2),
                          "billed_usd": float(billed) if isinstance(billed, (int, float)) else None})


def make_reader(provider: str):
    return OfflineReader() if provider == "offline" else ModelReader(provider)


# --------------------------------------------------------------------------
class ModelReader:
    def __init__(self, provider: str):
        self.provider = provider
        self.models = config.MODELS[provider]
        self.usage = Usage()
        self.last_error = ""
        if not self.models["fast"] or not self.models["strong"]:
            raise RuntimeError(f"Model names for '{provider}' are not set. See docs/MODEL_OPTIONS.md.")
        # Schema-constrained JSON output. Claude needs method="json_schema"; forced tool calling is not supported on every Claude model.
        extra = {"method": "json_schema"} if provider == "anthropic" else {}
        self._read = self._chat("fast", config.TEMP_READ).with_structured_output(BatchReadings, include_raw=True, **extra)
        self._reread = self._chat("strong", config.TEMP_READ).with_structured_output(CommentReading, include_raw=True, **extra)
        self._write = self._chat("strong", config.TEMP_FINDING).with_structured_output(Finding, include_raw=True, **extra)
        self._check = self._chat("fast", config.TEMP_EVALUATE).with_structured_output(Evaluation, include_raw=True, **extra)

    def _chat(self, role: str, temperature: float):
        if self.provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(model=self.models[role], temperature=temperature, max_tokens=4096, timeout=120, max_retries=3)
        from langchain_openai import ChatOpenAI
        if self.provider == "openrouter":
            return ChatOpenAI(model=self.models[role], temperature=temperature, timeout=120, max_retries=3,
                              base_url=config.OPENROUTER_BASE_URL, api_key=os.getenv("OPENROUTER_API_KEY"))
        return ChatOpenAI(model=self.models[role], temperature=temperature, timeout=120, max_retries=3)

    @staticmethod
    def _messages(prompt_name: str, payload) -> list:
        return [SystemMessage(_prompt(prompt_name)), HumanMessage(json.dumps(payload, ensure_ascii=False))]

    # step 2: parallelization. Batches run side by side; a failed batch is retried, then split.
    def read_batches(self, batches: list[list[dict]]) -> dict:
        out, failed, errors = {}, [], []
        started = time.time()
        inputs = [self._messages("classify", b) for b in batches]
        replies = self._read.batch(inputs, config={"max_concurrency": config.MAX_CONCURRENCY}, return_exceptions=True)
        for batch, reply in zip(batches, replies):
            parsed = None if isinstance(reply, Exception) else reply.get("parsed")
            if isinstance(reply, Exception):
                errors.append(_describe(reply))
            else:
                self.usage.add("fast", "read", reply.get("raw"))
                if not parsed:
                    errors.append(f"The reply did not match the expected format: {_describe(reply.get('parsing_error') or 'empty reply')}")
            got = {r.comment_id: r for r in parsed.readings} if parsed else {}
            for c in batch:
                if c["comment_id"] in got:
                    out[c["comment_id"]] = got[c["comment_id"]]
                else:
                    failed.append(c)
        # If not one comment was read, retrying them singly cannot help: stop and say why.
        if not out and errors:
            raise ModelError(f"The fast model could not read any comments. First error: {errors[0]}")
        # retry what failed, one comment at a time
        for c in failed:
            try:
                reply = self._read.invoke(self._messages("classify", [c]))
                self.usage.add("fast", "read", reply.get("raw"))
                parsed = reply.get("parsed")
                if parsed and parsed.readings:
                    r = parsed.readings[0]; r.comment_id = c["comment_id"]; out[c["comment_id"]] = r
            except Exception:
                pass
        self.usage.rows.append({"role": "fast", "step": "read_time", "calls": 0, "input_tokens": 0, "output_tokens": 0,
                                "seconds": round(time.time() - started, 2)})
        return out

    # step 3: routing target. One unclear comment at a time, stronger model.
    def reread(self, comment: dict, first: CommentReading | None) -> CommentReading | None:
        payload = {"comment": comment, "first_reading": first.model_dump(mode="json") if first else None}
        started = time.time()
        try:
            reply = self._reread.invoke(self._messages("reread", payload))
        except Exception as error:
            self.last_error = _describe(error)
            return None
        self.usage.add("strong", "reread", reply.get("raw"), time.time() - started)
        parsed = reply.get("parsed")
        if parsed:
            parsed.comment_id = comment["comment_id"]
        return parsed

    # step 6: prompt chaining. The model sees only the numbers and quotes code produced in step 5.
    def write_finding(self, evidence: dict, problems: list[str] | None = None) -> Finding | None:
        payload = {"data": evidence, "problems_with_previous_attempt": problems or []}
        started = time.time()
        try:
            reply = self._write.invoke(self._messages("finding", payload))
        except Exception:
            return None
        self.usage.add("strong", "finding", reply.get("raw"), time.time() - started)
        return reply.get("parsed")

    # step 7: evaluator. A second model checks the claims against the evidence.
    def evaluate(self, finding: Finding, evidence: dict) -> Evaluation:
        payload = {"finding": finding.model_dump(), "data": evidence}
        started = time.time()
        try:
            reply = self._check.invoke(self._messages("evaluate", payload))
        except Exception as error:
            return Evaluation(supported=False, problems=[f"The checker could not be reached: {type(error).__name__}"])
        self.usage.add("fast", "evaluate", reply.get("raw"), time.time() - started)
        return reply.get("parsed") or Evaluation(supported=False, problems=["The checker's reply could not be read."])


# --------------------------------------------------------------------------
FIT_RULES = [   # checked in this order; the first that matches is the fit reason
    ("fit_large", ["dheela", "dhila", "loose", "ढीला", "size bada nikla", "sack", "utar raha"]),
    ("fit_short", ["length bahut kam", "length bohot kam", "length bhot kam", "length bhi kam", "upar aa raha", "short", "chhoti", "kalai"]),
    ("fit_long", ["lamba hai", "lambi", "length zyada"]),
    ("fit_small", ["tight", "tite", "टाइट", "छोटा", "chota", "chhota", "chotta", "size bada lena", "fit nahi aa raha"]),
    ("fit_other", ["fitting ajeeb", "cut sahi nahi"]),
]
OTHER_RULES = [
    ("quality", ["kapda", "silai", "fabric", "stitching", "कपड़ा", "rang nikal", "sikud"]),
    ("colour", ["colour", "color", "kalar", "rang halka", "rang alag", "maroon"]),
    ("late", ["late", "der se", "arrived after"]),
    ("changed_mind", ["gift", "dusra pasand", "galti se"]),
    ("other", ["galat product", "tag nahi", "packet"]),
]
AREA_RULES = [("bust", ["bust", "chest"]), ("waist", ["kamar"]), ("shoulder", ["shoulder"]), ("sleeve", ["baju", "kalai"]),
              ("length", ["length", "ghutne", "lamba", "short", "zameen"])]


class OfflineReader:
    """Keyword rules standing in for the models, so the app runs with no API key.
    It only knows the phrases in the bundled stand-in data. It is not a model and costs nothing."""
    provider = "offline"
    models = {"fast": "keyword rules", "strong": "keyword rules"}

    def __init__(self):
        self.usage = Usage()

    def _one(self, comment: dict, second_look=False) -> CommentReading:
        text = comment["text"].lower()
        fit = next(((reason, k) for reason, keys in FIT_RULES for k in keys if k in text), None)
        others = [(reason, k) for reason, keys in OTHER_RULES for k in keys if k in text]
        others = list(dict(others).items())
        area = next((a for a, keys in AREA_RULES if any(k in text for k in keys)), "overall") if fit else "not_applicable"
        language = "hindi" if re.search(r"[ऀ-ॿ]", text) else ("english" if re.search(r"\b(the|is|too|and)\b", text) else "hinglish")
        base = dict(comment_id=comment["comment_id"], body_area=area, language=language,
                    meaning_en="Offline reader: no translation is available without a model.")
        if fit and others:
            return CommentReading(reason=fit[0], second_reason=others[0][0], confidence=0.88 if second_look else 0.62,
                                  evidence_phrase=f"{fit[1]} / {others[0][1]}", **base)
        if fit:
            return CommentReading(reason=fit[0], confidence=0.92, evidence_phrase=fit[1], **base)
        if others:
            return CommentReading(reason=others[0][0], confidence=0.90, evidence_phrase=others[0][1], **base)
        return CommentReading(reason="unclear", confidence=0.48 if second_look else 0.41, evidence_phrase="", **base)

    def read_batches(self, batches):
        started = time.time()
        out = {c["comment_id"]: self._one(c) for b in batches for c in b}
        self.usage.add("fast", "read", seconds=time.time() - started, calls=len(batches))
        return out

    def reread(self, comment, first):
        self.usage.add("strong", "reread")
        return self._one(comment, second_look=True)

    def write_finding(self, evidence, problems=None):
        self.usage.add("strong", "finding")
        e = evidence
        return Finding(
            headline=(f"{e['category']} from {e['vendor_id']}: {e['signal'].lower()}." if e["direction"]
                      else f"No clear fit pattern yet for {e['vendor_id']} {e['category']}."),
            evidence=(f"{e['fit_returns']} of {e['returns_read']} returns are about fit. The fit-return rate is {e['fit_return_rate_pct']}% "
                      f"against a {e['category']} median of {e['category_median_pct']}%."),
            suggested_fix=e["default_fix"])

    def evaluate(self, finding, evidence):
        self.usage.add("fast", "evaluate")
        return Evaluation(supported=True, problems=[])
