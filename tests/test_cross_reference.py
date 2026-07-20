"""Tests for cross-article edges and their persistence."""

from __future__ import annotations

import pytest

from ideagraph import (
    CrossReference,
    ProvenanceGraph,
    ProvenancePredicate,
    Statement,
)
from ideagraph.persistence import load_graph, save_graph


def test_cross_reference_target_parts_and_roundtrip():
    """A cross-reference exposes target parts and round-trips through a dict."""
    x = CrossReference(subject_id="c1", predicate=ProvenancePredicate.CITES, target="goncharov2022#f3")
    assert x.target_article == "goncharov2022"
    assert x.target_node == "f3"

    restored = CrossReference.from_dict(x.to_dict())
    assert restored.subject_id == "c1"
    assert restored.predicate is ProvenancePredicate.CITES
    assert restored.target == "goncharov2022#f3"
    assert restored.id == x.id


def test_graph_global_id_requires_article_id():
    """graph.global_id needs an article_id set."""
    g = ProvenanceGraph()
    g.add_statement(Statement(statement="x", id="c1"))
    with pytest.raises(ValueError, match="article_id"):
        g.global_id("c1")

    g.article_id = "paper1"
    assert g.global_id("c1") == "paper1#c1"


def test_persistence_roundtrips_article_and_cross_refs(tmp_path):
    """article_id, graph metadata, and cross-references survive save/load.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    g = ProvenanceGraph(article_id="paper1", metadata={"title": "Contamination"})
    g.add_statement(Statement(statement="Reported FARs are untrustworthy.", id="c1"))
    g.add_cross_reference(
        CrossReference(subject_id="c1", predicate=ProvenancePredicate.BUILDS_ON, target="goncharov2022#f3")
    )
    path = tmp_path / "g.json"
    save_graph(g, path)

    reloaded = load_graph(path)
    assert reloaded.article_id == "paper1"
    assert reloaded.metadata == {"title": "Contamination"}
    assert len(reloaded.cross_references) == 1
    x = next(iter(reloaded.cross_references.values()))
    assert x.subject_id == "c1"
    assert x.predicate is ProvenancePredicate.BUILDS_ON
    assert x.target == "goncharov2022#f3"


def test_pre_v3_graph_loads_without_article_fields(tmp_path):
    """A v2-style document (no article_id/cross_references) still loads.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    doc = tmp_path / "old.json"
    doc.write_text('{"schema_version": 2, "graph": {"statements": [{"statement": "x", "id": "c1"}]}}')
    g = load_graph(doc)
    assert g.article_id is None
    assert g.cross_references == {}
    assert "c1" in g.statements
