"""Tests for the :class:`claimkit.core.evidence.Evidence` model."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from claimkit.core import Claim, Evidence, EvidenceKind, EvidenceRelation


def test_defaults():
    """Evidence built from the required fields gets sensible defaults."""
    ev = Evidence(claim_id="c1", kind=EvidenceKind.CODE, reference="repo@abc123")
    assert ev.claim_id == "c1"
    assert ev.kind is EvidenceKind.CODE
    assert ev.reference == "repo@abc123"
    assert ev.relation is EvidenceRelation.SUPPORTS
    assert ev.description == ""
    assert ev.digest is None
    assert ev.metadata == {}
    assert ev.created_at.tzinfo is not None
    assert len(ev.id) == 32


def test_ids_are_unique():
    """Auto-generated identifiers differ between evidence records."""
    a = Evidence(claim_id="c1", kind=EvidenceKind.DATA, reference="a")
    b = Evidence(claim_id="c1", kind=EvidenceKind.DATA, reference="b")
    assert a.id != b.id


def test_links_to_a_claim_by_id():
    """Evidence references a claim by its id, not the object."""
    claim = Claim(statement="A", id="claim-001")
    ev = Evidence(claim_id=claim.id, kind=EvidenceKind.FIGURE, reference="fig1.png")
    assert ev.claim_id == claim.id


def test_to_dict_is_json_compatible():
    """to_dict() renders enums and the timestamp as stable tokens."""
    ev = Evidence(
        claim_id="c1",
        kind=EvidenceKind.LITERATURE,
        reference="10.1000/xyz",
        id="ev-001",
        relation=EvidenceRelation.REFUTES,
        description="counterexample",
        digest="sha256:deadbeef",
        metadata={"note": "n"},
    )
    data = ev.to_dict()
    assert data == {
        "id": "ev-001",
        "claim_id": "c1",
        "kind": "literature",
        "reference": "10.1000/xyz",
        "relation": "refutes",
        "description": "counterexample",
        "digest": "sha256:deadbeef",
        "created_at": ev.created_at.isoformat(),
        "metadata": {"note": "n"},
    }


def test_roundtrip_preserves_fields():
    """from_dict() inverts to_dict()."""
    original = Evidence(
        claim_id="c1",
        kind=EvidenceKind.WORKFLOW,
        reference="run-42",
        id="ev-001",
        relation=EvidenceRelation.CONTEXTUAL,
        description="background",
        digest="sha256:abc",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        metadata={"k": "v"},
    )
    restored = Evidence.from_dict(original.to_dict())
    assert restored == original


def test_roundtrip_with_null_digest():
    """A missing digest survives a serialisation round trip as None."""
    original = Evidence(claim_id="c1", kind=EvidenceKind.OTHER, reference="ref")
    restored = Evidence.from_dict(original.to_dict())
    assert restored.digest is None
    assert restored == original


@pytest.mark.parametrize("missing", ["claim_id", "kind", "reference"])
def test_from_dict_requires_core_fields(missing):
    """from_dict() raises when a required field is absent.

    Args:
        missing: The required key to drop from the input dictionary.

    """
    data = {"claim_id": "c1", "kind": "code", "reference": "r"}
    del data[missing]
    with pytest.raises(KeyError):
        Evidence.from_dict(data)


def test_from_dict_applies_defaults_for_missing_optionals():
    """Optional fields fall back to defaults when absent."""
    ev = Evidence.from_dict({"claim_id": "c1", "kind": "data", "reference": "r"})
    assert ev.relation is EvidenceRelation.SUPPORTS
    assert ev.description == ""
    assert ev.digest is None
    assert ev.metadata == {}
    assert len(ev.id) == 32


def test_to_dict_copies_metadata():
    """Mutating the dict output does not mutate the evidence."""
    ev = Evidence(claim_id="c1", kind=EvidenceKind.CODE, reference="r", metadata={"k": "v"})
    data = ev.to_dict()
    data["metadata"]["k2"] = "v2"
    assert ev.metadata == {"k": "v"}
