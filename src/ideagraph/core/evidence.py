"""Evidence supporting or refuting a :class:`~ideagraph.core.claim.Claim`.

A piece of :class:`Evidence` links a claim to a concrete research artefact —
code, data, a figure, a workflow run, a piece of literature, a human review, and
so on. It records *what* the artefact is (:class:`EvidenceKind`), *where* it
lives (a reference such as a path, URL, DOI, or commit hash), *how* it bears on
the claim (:class:`EvidenceRelation`), and an optional content digest so that a
later validation step can detect when the underlying artefact has changed.

Evidence references a claim by its ``id`` rather than holding a claim object, so
the two models stay decoupled and independently serialisable.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


class EvidenceKind(enum.StrEnum):
    """The type of artefact a piece of evidence points at.

    The value is a stable, machine-readable string token.

    Attributes:
        CODE: Source code, a script, or a commit.
        DATA: A dataset or data file.
        WORKFLOW: A workflow definition or an execution of one.
        ENVIRONMENT: A software environment specification (e.g. a lockfile).
        INSTRUMENT: A physical instrument or measurement apparatus.
        FIGURE: A figure or plot.
        TABLE: A table of results.
        LITERATURE: A publication or other external reference.
        HUMAN_REVIEW: An assessment recorded by a human reviewer.
        OTHER: Anything not covered by the categories above.
    """

    CODE = "code"
    DATA = "data"
    WORKFLOW = "workflow"
    ENVIRONMENT = "environment"
    INSTRUMENT = "instrument"
    FIGURE = "figure"
    TABLE = "table"
    LITERATURE = "literature"
    HUMAN_REVIEW = "human_review"
    OTHER = "other"


class EvidenceRelation(enum.StrEnum):
    """How a piece of evidence bears on the claim it is linked to.

    Attributes:
        SUPPORTS: The evidence backs the claim.
        REFUTES: The evidence contradicts the claim.
        CONTEXTUAL: The evidence is relevant background but neither supports nor
            refutes the claim on its own.
    """

    SUPPORTS = "supports"
    REFUTES = "refutes"
    CONTEXTUAL = "contextual"


def _utcnow() -> datetime:
    """Return the current time as a timezone-aware UTC datetime.

    Returns:
        The current moment in UTC.

    """
    return datetime.now(UTC)


@dataclass
class Evidence:
    """A link between a claim and a supporting or refuting artefact.

    Attributes:
        claim_id: The ``id`` of the :class:`~ideagraph.core.claim.Claim` this
            evidence bears on.
        kind: The type of artefact referenced.
        reference: A pointer to the artefact, e.g. a file path, URL, DOI, or
            commit hash.
        id: Stable unique identifier. Generated as a UUID4 hex string if not
            supplied.
        relation: How the evidence bears on the claim. Defaults to
            :attr:`EvidenceRelation.SUPPORTS`.
        description: A human-readable note about the evidence.
        digest: An optional content digest (e.g. a hash) of the artefact,
            captured so that later validation can detect when it has changed.
        created_at: Timezone-aware creation timestamp (UTC).
        metadata: Arbitrary structured metadata.
    """

    claim_id: str
    kind: EvidenceKind
    reference: str
    id: str = field(default_factory=lambda: uuid4().hex)
    relation: EvidenceRelation = EvidenceRelation.SUPPORTS
    description: str = ""
    digest: str | None = None
    created_at: datetime = field(default_factory=_utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialise the evidence to a JSON-compatible dictionary.

        Enums render as their stable string tokens and the timestamp as an
        ISO 8601 string, giving a representation suitable for exchange with
        other tools and autonomous agents.

        Returns:
            A dictionary representation of the evidence.

        """
        return {
            "id": self.id,
            "claim_id": self.claim_id,
            "kind": self.kind.value,
            "reference": self.reference,
            "relation": self.relation.value,
            "description": self.description,
            "digest": self.digest,
            "created_at": self.created_at.isoformat(),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Evidence:
        """Reconstruct evidence from its dictionary representation.

        This is the inverse of :meth:`to_dict`. ``claim_id``, ``kind``, and
        ``reference`` are required; any missing optional field falls back to its
        default.

        Args:
            data: A dictionary as produced by :meth:`to_dict`.

        Returns:
            The reconstructed evidence.

        Raises:
            KeyError: If ``claim_id``, ``kind``, or ``reference`` is missing.

        """
        kwargs: dict[str, Any] = {
            "claim_id": data["claim_id"],
            "kind": EvidenceKind(data["kind"]),
            "reference": data["reference"],
        }
        if "id" in data:
            kwargs["id"] = data["id"]
        if data.get("relation") is not None:
            kwargs["relation"] = EvidenceRelation(data["relation"])
        if data.get("description") is not None:
            kwargs["description"] = data["description"]
        if data.get("digest") is not None:
            kwargs["digest"] = data["digest"]
        if data.get("created_at") is not None:
            kwargs["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("metadata") is not None:
            kwargs["metadata"] = dict(data["metadata"])
        return cls(**kwargs)
