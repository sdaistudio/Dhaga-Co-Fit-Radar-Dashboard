"""Every record that crosses a model boundary or is saved to disk."""
from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, Field


class Reason(str, Enum):
    fit_small = "fit_small"
    fit_large = "fit_large"
    fit_short = "fit_short"
    fit_long = "fit_long"
    fit_other = "fit_other"
    quality = "quality"
    colour = "colour"
    late = "late"
    changed_mind = "changed_mind"
    other = "other"
    unclear = "unclear"


class BodyArea(str, Enum):
    bust = "bust"
    waist = "waist"
    hip = "hip"
    shoulder = "shoulder"
    sleeve = "sleeve"
    length = "length"
    overall = "overall"
    not_applicable = "not_applicable"


FIT_REASONS = {"fit_small", "fit_large", "fit_short", "fit_long", "fit_other"}

REASON_LABEL = {
    "fit_small": "Fit: too small", "fit_large": "Fit: too large", "fit_short": "Fit: too short",
    "fit_long": "Fit: too long", "fit_other": "Fit: other", "quality": "Quality", "colour": "Colour differs",
    "late": "Arrived late", "changed_mind": "Changed mind", "other": "Other", "unclear": "Unclear",
}


def reason_group(reason: str) -> str:
    """The six buckets shown on screen."""
    if reason in FIT_REASONS:
        return "fit"
    if reason in ("quality", "colour", "late"):
        return reason
    if reason == "unclear":
        return "person"
    return "other"


class CommentReading(BaseModel):
    """What a model returns for one comment."""
    comment_id: str
    reason: Reason
    second_reason: Optional[Reason] = None
    body_area: BodyArea = BodyArea.not_applicable
    language: Literal["hinglish", "hindi", "english", "other"] = "hinglish"
    confidence: float = Field(description="How sure you are of the reason, from 0 to 1")
    evidence_phrase: str = Field(description="Exact words from the comment that the reading relies on")
    meaning_en: str = Field(description="One short English sentence giving the meaning")


class BatchReadings(BaseModel):
    readings: list[CommentReading]


class Finding(BaseModel):
    """What the strong model writes for one vendor and category."""
    headline: str = Field(description="One sentence stating the fit pattern")
    evidence: str = Field(description="One or two sentences citing only numbers from the data given")
    suggested_fix: str = Field(description="One sentence: what to change on the size chart or listing")


class Evaluation(BaseModel):
    """What the fast model returns when checking a finding."""
    supported: bool
    problems: list[str] = []
