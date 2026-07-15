"""Tests for the :class:`claimkit.core.graph.ProvenanceGraph` aggregate."""

from __future__ import annotations

from claimkit.core import (
    Activity,
    ActivityKind,
    Claim,
    Evidence,
    EvidenceKind,
    EvidenceRelation,
    NodeType,
    ProvenanceGraph,
    ProvenancePredicate,
    ProvenanceRelation,
)


def _supports(claim_id: str, evidence_id: str, **overrides) -> ProvenanceRelation:
    """Build a claim-SUPPORTED_BY-evidence edge.

    Args:
        claim_id: Subject claim id.
        evidence_id: Object evidence id.
        **overrides: Fields to override on the edge.

    Returns:
        The edge.

    """
    return ProvenanceRelation(
        subject_type=NodeType.CLAIM,
        subject_id=claim_id,
        predicate=ProvenancePredicate.SUPPORTED_BY,
        object_type=NodeType.EVIDENCE,
        object_id=evidence_id,
        **overrides,
    )


def test_add_and_get_nodes():
    """Nodes are stored and retrievable by id."""
    g = ProvenanceGraph()
    claim = g.add_claim(Claim(statement="A", id="c1"))
    ev = g.add_evidence(Evidence(claim_id="c1", kind=EvidenceKind.DATA, reference="r", id="e1"))
    act = g.add_activity(Activity(kind=ActivityKind.COMPUTATION, label="l", id="a1"))
    assert g.claims["c1"] is claim
    assert g.evidence["e1"] is ev
    assert g.activities["a1"] is act


def test_add_node_replaces_same_id():
    """Adding a node with an existing id replaces it."""
    g = ProvenanceGraph()
    g.add_claim(Claim(statement="first", id="c1"))
    g.add_claim(Claim(statement="second", id="c1"))
    assert len(g.claims) == 1
    assert g.claims["c1"].statement == "second"


def test_outgoing_and_incoming():
    """Edges are indexed by both endpoints."""
    g = ProvenanceGraph()
    edge = g.add_relation(_supports("c1", "e1", id="edge-1"))
    assert g.outgoing("c1") == [edge]
    assert g.incoming("e1") == [edge]
    assert g.outgoing("e1") == []
    assert g.incoming("c1") == []


def test_outgoing_filters_by_predicate():
    """The predicate filter narrows the returned edges."""
    g = ProvenanceGraph()
    sup = g.add_relation(_supports("c1", "e1", id="s"))
    g.add_relation(
        ProvenanceRelation(
            subject_type=NodeType.CLAIM,
            subject_id="c1",
            predicate=ProvenancePredicate.REVIEWED_BY,
            object_type=NodeType.AGENT,
            object_id="agent-1",
            id="r",
        )
    )
    assert g.outgoing("c1", predicate=ProvenancePredicate.SUPPORTED_BY) == [sup]
    assert len(g.outgoing("c1")) == 2


def test_edges_preserve_insertion_order():
    """Multiple edges from a node keep insertion order."""
    g = ProvenanceGraph()
    a = g.add_relation(_supports("c1", "e1", id="a"))
    b = g.add_relation(_supports("c1", "e2", id="b"))
    assert g.outgoing("c1") == [a, b]


def test_add_relation_replaces_same_id_without_duplicating_index():
    """Re-adding an edge id updates the index instead of duplicating it."""
    g = ProvenanceGraph()
    g.add_relation(_supports("c1", "e1", id="edge-1"))
    g.add_relation(_supports("c1", "e2", id="edge-1"))
    edges = g.outgoing("c1")
    assert len(edges) == 1
    assert edges[0].object_id == "e2"
    assert g.incoming("e1") == []
    assert len(g.incoming("e2")) == 1


def test_evidence_for_returns_linked_evidence():
    """evidence_for follows supports/refutes edges to held evidence."""
    g = ProvenanceGraph()
    g.add_claim(Claim(statement="A", id="c1"))
    sup = g.add_evidence(Evidence(claim_id="c1", kind=EvidenceKind.DATA, reference="s", id="e1"))
    ref = g.add_evidence(Evidence(claim_id="c1", kind=EvidenceKind.DATA, reference="r", id="e2"))
    g.add_relation(_supports("c1", "e1", id="edge-1"))
    g.add_relation(
        ProvenanceRelation(
            subject_type=NodeType.CLAIM,
            subject_id="c1",
            predicate=ProvenancePredicate.REFUTED_BY,
            object_type=NodeType.EVIDENCE,
            object_id="e2",
            id="edge-2",
        )
    )
    assert g.evidence_for("c1") == [sup, ref]


def test_evidence_for_ignores_non_evidence_and_dangling():
    """evidence_for skips non-evidence edges and unheld references."""
    g = ProvenanceGraph()
    g.add_claim(Claim(statement="A", id="c1"))
    # Dangling: edge points at evidence id the graph does not hold.
    g.add_relation(_supports("c1", "missing", id="edge-1"))
    # Non-evidence predicate.
    g.add_relation(
        ProvenanceRelation(
            subject_type=NodeType.CLAIM,
            subject_id="c1",
            predicate=ProvenancePredicate.REVIEWED_BY,
            object_type=NodeType.AGENT,
            object_id="agent-1",
            id="edge-2",
        )
    )
    assert g.evidence_for("c1") == []


def test_dangling_edges_are_preserved():
    """Edges referencing unheld nodes are kept, not rejected."""
    g = ProvenanceGraph()
    edge = g.add_relation(_supports("c1", "e1", id="edge-1"))
    assert g.relations["edge-1"] is edge


def test_roundtrip_preserves_graph():
    """from_dict inverts to_dict for a fully populated graph."""
    g = ProvenanceGraph()
    g.add_claim(Claim(statement="A", id="c1"))
    g.add_evidence(
        Evidence(
            claim_id="c1",
            kind=EvidenceKind.DATA,
            reference="r",
            id="e1",
            relation=EvidenceRelation.SUPPORTS,
        )
    )
    g.add_activity(Activity(kind=ActivityKind.COMPUTATION, label="l", id="a1"))
    g.add_relation(_supports("c1", "e1", id="edge-1"))
    restored = ProvenanceGraph.from_dict(g.to_dict())
    assert restored == g
    # Index rebuilt: traversal still works after round trip.
    assert restored.outgoing("c1") == [restored.relations["edge-1"]]


def test_from_dict_tolerates_missing_collections():
    """from_dict treats absent collections as empty."""
    g = ProvenanceGraph.from_dict({})
    assert g == ProvenanceGraph()
