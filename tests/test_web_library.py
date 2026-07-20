"""Tests for the web Library view (cross-article idea graph)."""

from __future__ import annotations

import pytest

from ideagraph import CrossReference, ProvenanceGraph, ProvenancePredicate, Statement
from ideagraph.persistence import save_graph


def _library_dir(tmp_path):
    """Build a two-article library directory with a cross-reference.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    a = ProvenanceGraph(article_id="paperA")
    a.add_statement(Statement(statement="Builds on prior work.", id="c1"))
    a.add_cross_reference(CrossReference(subject_id="c1", predicate=ProvenancePredicate.BUILDS_ON, target="paperB#f1"))
    b = ProvenanceGraph(article_id="paperB")
    b.add_statement(Statement(statement="A cited finding.", id="f1"))
    save_graph(a, tmp_path / "A.json")
    save_graph(b, tmp_path / "B.json")
    return tmp_path


def test_build_library_payload_shape(tmp_path):
    """build_library_payload returns articles, nodes, cross edges, and counts.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    from ideagraph.web import build_library_payload

    payload = build_library_payload(_library_dir(tmp_path))
    assert {a["id"] for a in payload["articles"]} == {"paperA", "paperB"}
    assert {n["id"] for n in payload["nodes"]} == {"paperA#c1", "paperB#f1"}
    cross = [e for e in payload["edges"] if e["kind"] == "cross"]
    assert len(cross) == 1
    assert cross[0]["target"] == "paperB#f1"
    assert cross[0]["dangling"] is False
    assert payload["counts"]["cross_edges"] == 1


def test_config_and_library_routes(tmp_path):
    """/api/config advertises the library and /api/library serves the snapshot.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    pytest.importorskip("flask")
    from ideagraph.web import create_app

    client = create_app(library=_library_dir(tmp_path)).test_client()
    cfg = client.get("/api/config").get_json()
    assert cfg == {"graph": False, "library": True}

    assert client.get("/api/graph").status_code == 404  # no graph in this app
    lib = client.get("/api/library").get_json()
    assert lib["counts"]["statements"] == 2

    index = client.get("/")
    assert index.status_code == 200
    assert b"Library" in index.data
