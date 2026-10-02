"""Steps 3 and 4: every combination of confidence and second reason goes to the right place."""
import config
from fitradar import graph
from fitradar.schemas import CommentReading


def _reading(cid, reason="fit_small", confidence=0.9, second=None):
    return CommentReading(comment_id=cid, reason=reason, second_reason=second, confidence=confidence,
                          evidence_phrase="size chota", meaning_en="The size is small.")


class FakeReader:
    def __init__(self, first, second=None):
        self.first, self.second = first, second or {}

    def read_batches(self, batches):
        return {c["comment_id"]: self.first[c["comment_id"]] for b in batches for c in b if c["comment_id"] in self.first}

    def reread(self, comment, first):
        return self.second.get(comment["comment_id"])


def _state(ids, reader):
    results = {cid: {"comment_id": cid, "text": "size chota hai", "category": "Kurtis", "size": "M", "status": "pending",
                     "second_reason": None, "path": []} for cid in ids}
    return {"results": results, "reader": reader, "step_counts": {}, "step_seconds": {}}


def _first_read(first):
    state = _state(["sure", "edge", "unsure", "two", "said_unclear", "broken"], FakeReader(first))
    return graph.read(state)["results"]


FIRST = {
    "sure": _reading("sure", confidence=0.9),
    "edge": _reading("edge", confidence=config.CONF_ACCEPT),
    "unsure": _reading("unsure", confidence=config.CONF_ACCEPT - 0.01),
    "two": _reading("two", confidence=0.95, second="quality"),
    "said_unclear": _reading("said_unclear", reason="unclear", confidence=0.9),
    # "broken" has no reading: the reply failed validation
}


def test_first_read_routing():
    results = _first_read(FIRST)
    assert results["sure"]["status"] == "accepted"
    assert results["edge"]["status"] == "accepted"                 # at the threshold counts as sure
    assert results["unsure"]["status"] == "unclear"
    assert results["two"]["status"] == "unclear"                   # two reasons always get a second look
    assert results["said_unclear"]["status"] == "unclear"
    assert results["broken"]["status"] == "unclear_schema"


def test_graph_skips_reread_when_nothing_is_unclear():
    results = _state(["sure"], None)["results"]; results["sure"]["status"] = "accepted"
    assert graph.needs_reread({"results": results}) == "queue"
    results["sure"]["status"] = "unclear"
    assert graph.needs_reread({"results": results}) == "reread"


def test_reread_then_queue():
    state = _state(["now_sure", "still_unsure", "two", "failed"], None)
    for row in state["results"].values():
        row["status"] = "unclear"
    state["reader"] = FakeReader({}, {
        "now_sure": _reading("now_sure", confidence=0.85),
        "still_unsure": _reading("still_unsure", confidence=0.5),
        "two": _reading("two", confidence=0.88, second="quality"),
        # "failed": the strong model gave no usable reply
    })
    state.update(graph.reread(state))
    state.update(graph.queue(state))
    results = state["results"]
    assert results["now_sure"]["status"] == "accepted" and results["now_sure"]["read_by"] == "Strong model"
    assert results["two"]["status"] == "accepted" and results["two"]["second_reason"] == "quality"
    assert results["still_unsure"]["status"] == "queued" and results["still_unsure"]["read_by"] == "Review queue"
    assert results["failed"]["status"] == "queued"
    assert state["step_counts"]["4"] == "2 queued"


def test_every_comment_records_its_path():
    results = _first_read(FIRST)
    assert all(r["path"] for r in results.values())
    assert {step["by"] for r in results.values() for step in r["path"]} == {"Fast"}
