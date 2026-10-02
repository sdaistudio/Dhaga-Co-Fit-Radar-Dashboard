"""Every model reply is checked against these records. Valid replies pass; malformed ones are rejected."""
import pytest
from pydantic import ValidationError
from fitradar.schemas import BatchReadings, CommentReading, Evaluation, Finding, reason_group

GOOD = {"comment_id": "C-1", "reason": "fit_small", "second_reason": "quality", "body_area": "bust", "language": "hinglish",
        "confidence": 0.82, "evidence_phrase": "chest pe tight", "meaning_en": "It is tight at the chest."}


def test_valid_reading():
    r = CommentReading(**GOOD)
    assert r.reason.value == "fit_small" and r.second_reason.value == "quality"


def test_second_reason_is_optional():
    r = CommentReading(**{k: v for k, v in GOOD.items() if k != "second_reason"})
    assert r.second_reason is None


@pytest.mark.parametrize("field, value", [
    ("reason", "too_tight"),        # not one of the closed set
    ("body_area", "neck"),
    ("language", "tamil"),
    ("confidence", "very"),
])
def test_values_outside_the_closed_sets_are_rejected(field, value):
    with pytest.raises(ValidationError):
        CommentReading(**{**GOOD, field: value})


@pytest.mark.parametrize("missing", ["comment_id", "reason", "confidence", "evidence_phrase", "meaning_en"])
def test_required_fields(missing):
    with pytest.raises(ValidationError):
        CommentReading(**{k: v for k, v in GOOD.items() if k != missing})


def test_batch_of_readings():
    assert len(BatchReadings(readings=[GOOD, {**GOOD, "comment_id": "C-2"}]).readings) == 2
    with pytest.raises(ValidationError):
        BatchReadings(readings=[{"comment_id": "C-3"}])


def test_finding_needs_all_three_parts():
    Finding(headline="Kurtis from V-07 run small.", evidence="172 of 212 returns are about fit.", suggested_fix="Move the chart.")
    with pytest.raises(ValidationError):
        Finding(headline="Kurtis from V-07 run small.", evidence="172 of 212 returns are about fit.")


def test_evaluation():
    assert Evaluation(supported=True).problems == []
    assert Evaluation(supported=False, problems=["The figure 85 is not in the data."]).supported is False
    with pytest.raises(ValidationError):
        Evaluation(problems=[])


def test_reasons_fall_into_the_six_screen_groups():
    assert {reason_group(r) for r in ["fit_small", "fit_other"]} == {"fit"}
    assert reason_group("colour") == "colour" and reason_group("changed_mind") == "other"
    assert reason_group("unclear") == "person"
