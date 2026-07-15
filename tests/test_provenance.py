"""Tests for the :class:`claimkit.core.provenance.ProvenanceRelation` model."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from claimkit.core import NodeType, ProvenancePredicate, ProvenanceRelation


def _edge(**overrides):
    """Build a claim-supported-by-evidence edge with optional overrides.

    Args:
        **overrides: Fields to override on the default edge.

    Returns:
        A :class:`ProvenanceRelation`.

    """
    defaults = {
        "subject_type": NodeType.CLAIM,
        "subject_id": "claim-1",
        "predicate": ProvenancePredicate.SUPPORTED_BY,
        "object_type": NodeType.EVIDENCE,
        "object_id": "ev-1",
    }
    defaults.update(overrides)
    return ProvenanceRelation(**defaults)


def test_defaults():
    """An edge built from the required fields gets sensible defaults."""
    edge = _edge()
    assert edge.subject_type is NodeType.CLAIM
    assert edge.subject_id == "claim-1"
    assert edge.predicate is ProvenancePredicate.SUPPORTED_BY
    assert edge.object_type is NodeType.EVIDENCE
    assert edge.object_id == "ev-1"
    assert edge.metadata == {}
    assert edge.created_at.tzinfo is not None
    assert len(edge.id) == 32


def test_ids_are_unique():
    """Auto-generated identifiers differ between edges."""
    assert _edge().id != _edge().id


def test_directionality_is_preserved():
    """Subject and object endpoints keep their roles."""
    edge = _edge(
        subject_type=NodeType.EVIDENCE,
        subject_id="ev-1",
        predicate=ProvenancePredicate.GENERATED_BY,
        object_type=NodeType.ACTIVITY,
        object_id="act-1",
    )
    assert edge.subject_id == "ev-1"
    assert edge.object_id == "act-1"
    assert edge.predicate is ProvenancePredicate.GENERATED_BY


def test_to_dict_is_json_compatible():
    """to_dict() renders node types and predicate as stable tokens."""
    edge = _edge(id="edge-1", metadata={"k": "v"})
    data = edge.to_dict()
    assert data == {
        "id": "edge-1",
        "subject_type": "claim",
        "subject_id": "claim-1",
        "predicate": "supported_by",
        "object_type": "evidence",
        "object_id": "ev-1",
        "created_at": edge.created_at.isoformat(),
        "metadata": {"k": "v"},
    }


def test_roundtrip_preserves_fields():
    """from_dict() inverts to_dict()."""
    original = _edge(
        id="edge-1",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        metadata={"k": "v"},
    )
    restored = ProvenanceRelation.from_dict(original.to_dict())
    assert restored == original


@pytest.mark.parametrize(
    "missing",
    ["subject_type", "subject_id", "predicate", "object_type", "object_id"],
)
def test_from_dict_requires_core_fields(missing):
    """from_dict() raises when a required field is absent.

    Args:
        missing: The required key to drop from the input dictionary.

    """
    data = _edge().to_dict()
    del data[missing]
    with pytest.raises(KeyError):
        ProvenanceRelation.from_dict(data)


def test_from_dict_applies_defaults_for_missing_optionals():
    """Optional fields fall back to defaults when absent."""
    edge = ProvenanceRelation.from_dict(
        {
            "subject_type": "activity",
            "subject_id": "act-1",
            "predicate": "used",
            "object_type": "artefact",
            "object_id": "data-1",
        }
    )
    assert edge.metadata == {}
    assert len(edge.id) == 32


def test_to_dict_copies_metadata():
    """Mutating the dict output does not mutate the edge."""
    edge = _edge(metadata={"k": "v"})
    data = edge.to_dict()
    data["metadata"]["k2"] = "v2"
    assert edge.metadata == {"k": "v"}
