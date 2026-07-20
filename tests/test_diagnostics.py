"""Tests for graph integrity diagnostics (``diagnose`` / ``doctor``)."""

from __future__ import annotations

from ideagraph import (
    CrossReference,
    NodeType,
    ProvenanceGraph,
    ProvenancePredicate,
    ProvenanceRelation,
    Statement,
    diagnose,
)


def _codes(graph, **kw):
    """Return the set of diagnostic codes for a graph.

    Args:
        graph: The graph to diagnose.
        **kw: Passed through to ``diagnose``.

    """
    return {d.code for d in diagnose(graph, **kw)}


def test_clean_graph_has_no_diagnostics():
    """A well-formed single-article graph reports nothing."""
    g = ProvenanceGraph(article_id="paper1")
    g.add_statement(Statement(statement="x", id="c1"))
    g.add_statement(Statement(statement="y", id="c2"))
    g.add_cross_reference(CrossReference(subject_id="c1", predicate=ProvenancePredicate.CITES, target="other#n1"))
    assert diagnose(g) == []


def test_dangling_xref_subject_is_error():
    """A cross-reference from a missing statement is an error."""
    g = ProvenanceGraph(article_id="paper1")
    g.add_cross_reference(CrossReference(subject_id="ghost", predicate=ProvenancePredicate.CITES, target="other#n1"))
    assert "xref-dangling-subject" in _codes(g)


def test_bad_target_is_error():
    """A malformed global target is an error."""
    g = ProvenanceGraph(article_id="paper1")
    g.add_statement(Statement(statement="x", id="c1"))
    g.add_cross_reference(CrossReference(subject_id="c1", predicate=ProvenancePredicate.CITES, target="no-separator"))
    assert "xref-bad-target" in _codes(g)


def test_self_reference_into_missing_node_is_error():
    """A cross-reference into this article at a missing node is an error."""
    g = ProvenanceGraph(article_id="paper1")
    g.add_statement(Statement(statement="x", id="c1"))
    g.add_cross_reference(
        CrossReference(subject_id="c1", predicate=ProvenancePredicate.SAME_AS, target="paper1#missing")
    )
    assert "xref-self-dangling" in _codes(g)


def test_no_article_id_with_xrefs_warns():
    """Outward links from a graph with no article_id warn."""
    g = ProvenanceGraph()
    g.add_statement(Statement(statement="x", id="c1"))
    g.add_cross_reference(CrossReference(subject_id="c1", predicate=ProvenancePredicate.CITES, target="other#n1"))
    assert "no-article-id" in _codes(g)


def test_unknown_article_warns_only_with_library_context():
    """xref-unknown-article fires only when known_articles is provided."""
    g = ProvenanceGraph(article_id="paper1")
    g.add_statement(Statement(statement="x", id="c1"))
    g.add_cross_reference(CrossReference(subject_id="c1", predicate=ProvenancePredicate.CITES, target="other#n1"))
    assert "xref-unknown-article" not in _codes(g)  # single-graph: not checked
    assert "xref-unknown-article" in _codes(g, known_articles={"paper1"})  # library: 'other' missing
    assert "xref-unknown-article" not in _codes(g, known_articles={"paper1", "other"})


def test_dangling_intra_relation_warns():
    """An intra-article edge to a missing evidence node warns."""
    g = ProvenanceGraph(article_id="paper1")
    g.add_statement(Statement(statement="x", id="c1"))
    g.add_relation(
        ProvenanceRelation(
            subject_type=NodeType.CLAIM,
            subject_id="c1",
            predicate=ProvenancePredicate.SUPPORTED_BY,
            object_type=NodeType.EVIDENCE,
            object_id="missing-ev",
        )
    )
    assert "relation-dangling-object" in _codes(g)
