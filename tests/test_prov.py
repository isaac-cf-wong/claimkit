"""Tests for :mod:`ideagraph.prov` (PROV-JSON export)."""

from __future__ import annotations

import json
from datetime import UTC, datetime

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
from ideagraph.prov import CK_NAMESPACE, dumps_prov, to_prov


def _edge(subject, predicate, obj, edge_id):
    """Build a provenance edge.

    Args:
        subject: Subject endpoint as ``(NodeType, id)``.
        predicate: Edge predicate.
        obj: Object endpoint as ``(NodeType, id)``.
        edge_id: Edge id.

    Returns:
        The edge.

    """
    subject_type, subject_id = subject
    object_type, object_id = obj
    return ProvenanceRelation(
        subject_type=subject_type,
        subject_id=subject_id,
        predicate=predicate,
        object_type=object_type,
        object_id=object_id,
        id=edge_id,
    )


def test_prefix_is_declared():
    """The document declares the ck namespace prefix."""
    doc = to_prov(ProvenanceGraph())
    assert doc["prefix"] == {"ck": CK_NAMESPACE}


def test_claim_and_evidence_become_entities():
    """Claims and evidence map to prov:Entity with ideagraph attributes."""
    g = ProvenanceGraph()
    g.add_claim(Claim(statement="A", id="c1", status=ClaimStatus.VALID))
    g.add_evidence(Evidence(claim_id="c1", kind=EvidenceKind.DATA, reference="r", id="e1", digest="sha256:aa"))
    doc = to_prov(g)
    assert doc["entity"]["ck:c1"] == {
        "prov:type": "ck:Claim",
        "ck:statement": "A",
        "ck:status": "valid",
    }
    assert doc["entity"]["ck:e1"] == {
        "prov:type": "ck:Evidence",
        "ck:kind": "data",
        "ck:reference": "r",
        "ck:digest": "sha256:aa",
    }


def test_evidence_without_digest_omits_key():
    """Evidence with no digest omits the ck:digest attribute."""
    g = ProvenanceGraph()
    g.add_evidence(Evidence(claim_id="c1", kind=EvidenceKind.DATA, reference="r", id="e1"))
    assert "ck:digest" not in to_prov(g)["entity"]["ck:e1"]


def test_activity_maps_with_times():
    """Activities map to prov:Activity with label and time interval."""
    g = ProvenanceGraph()
    g.add_activity(
        Activity(
            kind=ActivityKind.COMPUTATION,
            label="run",
            id="a1",
            started_at=datetime(2026, 1, 1, tzinfo=UTC),
            ended_at=datetime(2026, 1, 2, tzinfo=UTC),
        )
    )
    assert to_prov(g)["activity"]["ck:a1"] == {
        "prov:type": "ck:Activity",
        "prov:label": "run",
        "prov:startTime": "2026-01-01T00:00:00+00:00",
        "prov:endTime": "2026-01-02T00:00:00+00:00",
    }


def test_generated_by_and_used_relations():
    """GENERATED_BY and USED map to their PROV relations."""
    g = ProvenanceGraph()
    g.add_evidence(Evidence(claim_id="c1", kind=EvidenceKind.DATA, reference="r", id="e1"))
    g.add_activity(Activity(kind=ActivityKind.COMPUTATION, label="run", id="a1"))
    g.add_relation(_edge((NodeType.EVIDENCE, "e1"), ProvenancePredicate.GENERATED_BY, (NodeType.ACTIVITY, "a1"), "g1"))
    g.add_relation(_edge((NodeType.ACTIVITY, "a1"), ProvenancePredicate.USED, (NodeType.ARTEFACT, "data-1"), "u1"))
    doc = to_prov(g)
    assert doc["wasGeneratedBy"]["ck:g1"] == {"prov:entity": "ck:e1", "prov:activity": "ck:a1"}
    assert doc["used"]["ck:u1"] == {"prov:activity": "ck:a1", "prov:entity": "ck:data-1"}
    # The artefact endpoint is materialised as an entity stub.
    assert doc["entity"]["ck:data-1"] == {"prov:type": "ck:Artefact"}


def test_attributed_to_creates_agent_stub():
    """ATTRIBUTED_TO maps to wasAttributedTo and stubs the agent."""
    g = ProvenanceGraph()
    g.add_claim(Claim(statement="A", id="c1"))
    g.add_relation(_edge((NodeType.CLAIM, "c1"), ProvenancePredicate.ATTRIBUTED_TO, (NodeType.AGENT, "alice"), "at1"))
    doc = to_prov(g)
    assert doc["wasAttributedTo"]["ck:at1"] == {"prov:entity": "ck:c1", "prov:agent": "ck:alice"}
    assert doc["agent"]["ck:alice"] == {"prov:type": "ck:Agent"}


def test_derived_from_relation():
    """DERIVED_FROM maps to wasDerivedFrom."""
    g = ProvenanceGraph()
    g.add_relation(_edge((NodeType.ARTEFACT, "a"), ProvenancePredicate.DERIVED_FROM, (NodeType.ARTEFACT, "b"), "d1"))
    assert to_prov(g)["wasDerivedFrom"]["ck:d1"] == {
        "prov:generatedEntity": "ck:a",
        "prov:usedEntity": "ck:b",
    }


def test_ideagraph_predicates_become_influence_with_note():
    """SUPPORTED_BY/REFUTED_BY export as wasInfluencedBy with ck:predicate."""
    g = ProvenanceGraph()
    g.add_claim(Claim(statement="A", id="c1"))
    g.add_evidence(Evidence(claim_id="c1", kind=EvidenceKind.DATA, reference="r", id="e1"))
    g.add_relation(_edge((NodeType.CLAIM, "c1"), ProvenancePredicate.SUPPORTED_BY, (NodeType.EVIDENCE, "e1"), "s1"))
    doc = to_prov(g)
    assert doc["wasInfluencedBy"]["ck:s1"] == {
        "prov:influencee": "ck:c1",
        "prov:influencer": "ck:e1",
        "ck:predicate": "supported_by",
    }


def test_empty_collections_are_omitted():
    """Only non-empty collections appear in the document."""
    doc = to_prov(ProvenanceGraph())
    assert set(doc) == {"prefix"}


def test_dumps_prov_is_valid_json():
    """dumps_prov produces parseable JSON matching to_prov."""
    g = ProvenanceGraph()
    g.add_claim(Claim(statement="A", id="c1"))
    assert json.loads(dumps_prov(g)) == to_prov(g)
