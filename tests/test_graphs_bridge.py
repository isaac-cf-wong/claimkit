"""Tests for the ORM<->ProvenanceGraph bridge and import/export commands."""

from __future__ import annotations

import pytest
from django.core.management import call_command

from ideagraph.core import (
    Activity,
    ActivityKind,
    CrossReference,
    Evidence,
    EvidenceKind,
    NodeType,
    ProvenanceGraph,
    ProvenancePredicate,
    ProvenanceRelation,
    Statement,
    StatementStatus,
    StatementType,
)
from ideagraph.persistence import save_graph
from ideagraph.server.graphs.bridge import graph_to_orm, orm_to_graph
from ideagraph.server.graphs.models import Edge, Graph, Node


def _sample_graph() -> ProvenanceGraph:
    """Build a graph exercising every node and edge kind.

    Returns:
        The graph.

    """
    g = ProvenanceGraph(article_id="art1", metadata={"title": "Demo"})
    g.add_statement(Statement(statement="A claim.", id="c1", type=StatementType.CLAIM, status=StatementStatus.VALID))
    g.add_evidence(Evidence(claim_id="c1", kind=EvidenceKind.DATA, reference="data.csv", id="e1", digest="sha256:aa"))
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
    g.add_cross_reference(
        CrossReference(subject_id="c1", predicate=ProvenancePredicate.BUILDS_ON, target="art2#c9", id="x1")
    )
    return g


@pytest.mark.django_db
def test_bridge_roundtrip_preserves_graph():
    """orm_to_graph inverts graph_to_orm."""
    original = _sample_graph()
    row = graph_to_orm(original, slug="demo")
    restored = orm_to_graph(row)
    assert restored == original


@pytest.mark.django_db
def test_denormalised_columns_populated():
    """Node/Edge denormalised columns are filled from the data dicts."""
    graph_to_orm(_sample_graph(), slug="demo")
    statement = Node.objects.get(node_id="c1")
    assert statement.kind == Node.Kind.STATEMENT
    assert statement.stype == "claim"
    assert statement.status == "valid"
    assert statement.text == "A claim."
    evidence = Node.objects.get(node_id="e1")
    assert evidence.kind == Node.Kind.EVIDENCE
    assert evidence.text == "data.csv"
    relation = Edge.objects.get(edge_id="edge-1")
    assert relation.edge_class == Edge.EdgeClass.RELATION
    assert relation.subject_id == "c1"
    assert relation.predicate == "supported_by"
    assert relation.object_ref == "e1"
    xref = Edge.objects.get(edge_id="x1")
    assert xref.edge_class == Edge.EdgeClass.CROSS_REFERENCE
    assert xref.object_ref == "art2#c9"


@pytest.mark.django_db
def test_graph_metadata_persisted():
    """Graph-level article_id/title/metadata are stored."""
    row = graph_to_orm(_sample_graph(), slug="demo")
    assert row.article_id == "art1"
    assert row.title == "Demo"
    assert row.metadata["title"] == "Demo"


@pytest.mark.django_db
def test_reimport_replaces_existing():
    """Importing the same slug replaces the previous rows."""
    graph_to_orm(_sample_graph(), slug="demo")
    smaller = ProvenanceGraph(article_id="art1")
    smaller.add_statement(Statement(statement="Only one.", id="c1"))
    graph_to_orm(smaller, slug="demo")
    assert Graph.objects.filter(slug="demo").count() == 1
    assert Node.objects.filter(graph__slug="demo").count() == 1
    assert Edge.objects.filter(graph__slug="demo").count() == 0


@pytest.mark.django_db
def test_import_then_export_command_roundtrip(tmp_path):
    """import_graph then export_graph reproduces the graph on disk.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    from ideagraph.persistence import load_graph

    src = tmp_path / "in.json"
    save_graph(_sample_graph(), src)
    call_command("import_graph", "demo", str(src))
    out = tmp_path / "out.json"
    call_command("export_graph", "demo", str(out))
    # Compare the two serialised graphs (timestamps preserved through JSON).
    assert load_graph(out) == load_graph(src)
