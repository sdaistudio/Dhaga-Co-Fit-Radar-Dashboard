"""A person's tag in the review queue must become a reason the counting code understands."""
from fitradar.graph import TAG_TO_REASON
from fitradar.schemas import FIT_REASONS, Reason


def test_every_tag_maps_to_a_real_reason():
    assert all(Reason(v) for v in TAG_TO_REASON.values())


def test_fit_direction_tags_keep_their_direction():
    assert TAG_TO_REASON["Fit: too small"] == "fit_small"
    assert TAG_TO_REASON["Fit: too large"] == "fit_large"
    assert TAG_TO_REASON["Fit: too short"] == "fit_short"
    assert TAG_TO_REASON["Fit: too long"] == "fit_long"
    assert all(TAG_TO_REASON[t] in FIT_REASONS for t in TAG_TO_REASON if t.startswith("Fit"))


def test_older_plain_fit_tag_still_counts_as_fit_without_direction():
    assert TAG_TO_REASON["Fit"] == "fit_other"
