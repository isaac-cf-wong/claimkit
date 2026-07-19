"""Tests for :mod:`ideagraph.persistence`."""

from __future__ import annotations

import json

import pytest

from ideagraph.core import (
    Activity,
    ActivityKind,
    Claim,
    ClaimStatus,
    Evidence,
    EvidenceKind,
    NodeType,
    ProvenanceGraph,
    ProvenancePredicate,
    ProvenanceRelation,
)
from ideagraph.persistence import (
    SCHEMA_VERSION,
    dumps_graph,
    graph_from_document,
    load_graph,
    loads_graph,
    save_graph,
)


def _populated_graph() -> ProvenanceGraph:
    """Build a graph exercising every node and edge type.

    Returns:
        The graph.

    """
    g = ProvenanceGraph()
    g.add_claim(Claim(statement="A", id="c1", status=ClaimStatus.VALID))
    g.add_evidence(Evidence(claim_id="c1", kind=EvidenceKind.DATA, reference="r", id="e1", digest="sha256:abc"))
    g.add_activity(Activity(kind=ActivityKind.COMPUTATION, label="run", id="a1"))
    g.add_relation(
        ProvenanceRelation(
            subject_type=NodeType.CLAIM,
            subject_id="c1",
            predicate=ProvenancePredicate.SUPPORTED_BY,
            object_type=NodeType.EVIDENCE,
            object_id="e1",
            id="edge-1",
        )
    )
    return g


def test_string_roundtrip():
    """loads_graph inverts dumps_graph."""
    g = _populated_graph()
    restored = loads_graph(dumps_graph(g))
    assert restored == g


def test_dumps_includes_version_envelope():
    """The serialised document carries the schema version and graph."""
    g = _populated_graph()
    doc = json.loads(dumps_graph(g))
    assert doc["schema_version"] == SCHEMA_VERSION
    assert "graph" in doc
    assert {s["id"] for s in doc["graph"]["statements"]} == {"c1"}


def test_file_roundtrip(tmp_path):
    """save_graph then load_graph reconstructs the graph.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    g = _populated_graph()
    path = tmp_path / "nested" / "graph.json"
    save_graph(g, path)
    assert path.exists()
    assert load_graph(path) == g


def test_saved_file_ends_with_newline(tmp_path):
    """The saved file has a trailing newline.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    path = tmp_path / "graph.json"
    save_graph(ProvenanceGraph(), path)
    assert path.read_text(encoding="utf-8").endswith("}\n")


def test_traversal_works_after_load(tmp_path):
    """A loaded graph has its traversal index rebuilt.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    path = tmp_path / "graph.json"
    save_graph(_populated_graph(), path)
    restored = load_graph(path)
    assert [e.id for e in restored.outgoing("c1")] == ["edge-1"]


def test_newer_schema_version_rejected():
    """A document from a newer schema version is refused."""
    doc = {"schema_version": SCHEMA_VERSION + 1, "graph": ProvenanceGraph().to_dict()}
    with pytest.raises(ValueError, match="newer than supported"):
        graph_from_document(doc)


def test_missing_envelope_keys_raise():
    """A document missing required envelope keys raises KeyError."""
    with pytest.raises(KeyError):
        graph_from_document({"graph": ProvenanceGraph().to_dict()})


def test_empty_graph_roundtrip():
    """An empty graph survives a round trip."""
    assert loads_graph(dumps_graph(ProvenanceGraph())) == ProvenanceGraph()
