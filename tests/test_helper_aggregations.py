# tests/test_helper_aggregations.py
"""Unit tests for opensearch.helper.run_aggregations."""

from opensearch import helper
from tools.tool_params import AggregationsArgs


class FakeClient:
    """Fake OpenSearch client capturing search() calls."""

    def __init__(self):
        """Init with an empty call log."""
        self.calls = []

    def search(self, index, body, **kwargs):
        """Record the call and return a canned aggregations response."""
        self.calls.append((index, body))
        return {"took": 7, "timed_out": False, "aggregations": {"x": {"value": 1}}}


def test_run_aggregations_builds_body(monkeypatch):
    """Helper should build size:0 body with optional query/timeout/track_total_hits."""
    fake = FakeClient()
    monkeypatch.setattr("opensearch.client.initialize_client", lambda args: fake)

    args = AggregationsArgs(
        index="idx",
        aggs={"a": {"terms": {"field": "user"}}},
        query={"term": {"status": "ok"}},
        track_total_hits=True,
        timeout="5s",
        raw=False,
    )
    resp = helper.run_aggregations(args)
    assert resp["aggregations"] == {"x": {"value": 1}}

    assert len(fake.calls) == 1
    index, body = fake.calls[0]
    assert index == "idx"
    assert body["size"] == 0
    assert body["aggs"] == {"a": {"terms": {"field": "user"}}}
    assert body["query"] == {"term": {"status": "ok"}}
    assert body["track_total_hits"] is True
    assert body["timeout"] == "5s"
