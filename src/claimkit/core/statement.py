"""The :class:`Statement`, claimkit's primary abstraction (v-next).

A statement is a typed block of an article — a claim, a piece of background, a
method, a definition, and so on — registered independently of any manuscript. It
carries a stable identity, its text, a :class:`StatementType`, a validation
status, reading order, and structured metadata. Supporting evidence and
provenance / discourse relationships are attached by other parts of the
framework; this module defines only the statement itself and its serialisable
representation.

``Claim`` is retained as a backward-compatible alias for ``Statement`` (a claim
is the ``StatementType.CLAIM`` case), and ``ClaimStatus`` for
:class:`StatementStatus`.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


class StatementStatus(enum.StrEnum):
    """Validation status of a statement.

    Reflects the relationship between a (claim/finding) statement and its current
    supporting evidence. A plain string enum for stable, machine-readable tokens.

    Attributes:
        UNRESOLVED: Not yet validated against evidence.
        VALID: Supported by the current evidence.
        STALE: Supporting evidence changed; must be re-validated.
        INVALID: The current evidence contradicts the statement.
        NEEDS_REVIEW: Automated validation is inconclusive; a human must decide.
    """

    UNRESOLVED = "unresolved"
    VALID = "valid"
    STALE = "stale"
    INVALID = "invalid"
    NEEDS_REVIEW = "needs_review"


class StatementType(enum.StrEnum):
    """The rhetorical role a statement plays in the article.

    A small, opinionated set; extend deliberately rather than open-endedly.

    Attributes:
        CLAIM: An assertion the paper argues for.
        FINDING: A specific result-backed conclusion.
        BACKGROUND: Prior context, typically literature-backed.
        METHOD: A description of how something was done.
        DEFINITION: A definition or notation.
        MOTIVATION: Why the work matters / the gap.
        RESULT: A reported measurement or outcome.
        OTHER: Anything not covered above.
    """

    CLAIM = "claim"
    FINDING = "finding"
    BACKGROUND = "background"
    METHOD = "method"
    DEFINITION = "definition"
    MOTIVATION = "motivation"
    RESULT = "result"
    OTHER = "other"


def _utcnow() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(UTC)


@dataclass
class Statement:
    """A registered, typed statement — the primary unit of a claimkit graph.

    Attributes:
        statement: The statement's text (a block of one or more sentences).
        id: Stable unique identifier (UUID4 hex if not supplied).
        type: The statement's :class:`StatementType` (defaults to ``CLAIM``).
        status: Validation status (defaults to ``UNRESOLVED``).
        order: Reading-order index within the article (defaults to 0).
        section: Optional section label.
        source_digest: Optional ``sha256:`` of the draft span the text came from,
            for detecting drift between the graph and the manuscript.
        created_at: Timezone-aware creation timestamp (UTC).
        updated_at: Timezone-aware timestamp of the last status change (UTC).
        tags: Free-form labels.
        metadata: Arbitrary structured metadata.
    """

    statement: str
    id: str = field(default_factory=lambda: uuid4().hex)
    type: StatementType = StatementType.CLAIM
    status: StatementStatus = StatementStatus.UNRESOLVED
    order: int = 0
    section: str | None = None
    source_digest: str | None = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def mark(self, status: StatementStatus) -> None:
        """Set the validation status and refresh :attr:`updated_at`.

        Args:
            status: The new validation status.
        """
        self.status = StatementStatus(status)
        self.updated_at = _utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-compatible dictionary.

        Returns:
            A dictionary representation of the statement.
        """
        return {
            "id": self.id,
            "statement": self.statement,
            "type": self.type.value,
            "status": self.status.value,
            "order": self.order,
            "section": self.section,
            "source_digest": self.source_digest,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tags": list(self.tags),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Statement:
        """Reconstruct a statement from its dictionary representation.

        Inverse of :meth:`to_dict`. Only ``statement`` is required; a missing
        ``type`` defaults to ``CLAIM`` (so pre-v-next ``claims`` migrate cleanly).

        Args:
            data: A dictionary as produced by :meth:`to_dict`.

        Returns:
            The reconstructed statement.

        Raises:
            KeyError: If ``statement`` is missing from ``data``.
        """
        kwargs: dict[str, Any] = {"statement": data["statement"]}
        if "id" in data:
            kwargs["id"] = data["id"]
        if data.get("type") is not None:
            kwargs["type"] = StatementType(data["type"])
        if data.get("status") is not None:
            kwargs["status"] = StatementStatus(data["status"])
        if data.get("order") is not None:
            kwargs["order"] = int(data["order"])
        if data.get("section") is not None:
            kwargs["section"] = data["section"]
        if data.get("source_digest") is not None:
            kwargs["source_digest"] = data["source_digest"]
        if data.get("created_at") is not None:
            kwargs["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at") is not None:
            kwargs["updated_at"] = datetime.fromisoformat(data["updated_at"])
        if data.get("tags") is not None:
            kwargs["tags"] = list(data["tags"])
        if data.get("metadata") is not None:
            kwargs["metadata"] = dict(data["metadata"])
        return cls(**kwargs)
