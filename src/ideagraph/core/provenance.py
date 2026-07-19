"""Typed provenance edges connecting ideagraph's nodes into a graph.

The claim, evidence, and activity models are the *nodes* of a provenance graph.
A :class:`ProvenanceRelation` is a directed, typed *edge* between two of those
nodes (plus artefacts and agents), e.g. a claim ``SUPPORTED_BY`` a piece of
evidence, or evidence ``GENERATED_BY`` an activity.

Edges reference their endpoints by identifier and also record each endpoint's
:class:`NodeType`, so an autonomous agent can traverse the graph — following an
edge in either direction and knowing what kind of node sits at each end —
without having to load the node objects themselves. The predicate vocabulary is
drawn from `PROV-DM <https://www.w3.org/TR/prov-dm/>`_ where a natural
correspondence exists, easing later export to established provenance standards.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


class NodeType(enum.StrEnum):
    """The kind of node sitting at an end of a provenance edge.

    Attributes:
        CLAIM: A :class:`~ideagraph.core.claim.Claim`.
        EVIDENCE: A piece of :class:`~ideagraph.core.evidence.Evidence`.
        ACTIVITY: An :class:`~ideagraph.core.activity.Activity`.
        ARTEFACT: A research artefact (dataset, figure, commit, ...).
        AGENT: A person, tool, or autonomous agent.
    """

    CLAIM = "claim"
    EVIDENCE = "evidence"
    ACTIVITY = "activity"
    ARTEFACT = "artefact"
    AGENT = "agent"


class ProvenancePredicate(enum.StrEnum):
    """The typed relationship a provenance edge expresses.

    Where a natural correspondence exists, the token mirrors a `PROV-DM
    <https://www.w3.org/TR/prov-dm/>`_ relation to ease later export.

    Attributes:
        SUPPORTED_BY: The subject claim is supported by the object evidence.
        REFUTED_BY: The subject claim is refuted by the object evidence.
        GENERATED_BY: The subject was produced by the object activity
            (PROV ``wasGeneratedBy``).
        USED: The subject activity consumed the object artefact (PROV ``used``).
        DERIVED_FROM: The subject was derived from the object
            (PROV ``wasDerivedFrom``).
        ATTRIBUTED_TO: The subject is attributed to the object agent
            (PROV ``wasAttributedTo``).
        REVIEWED_BY: The subject was reviewed by the object agent or activity.
        RELATES_TO: A generic association with no more specific predicate.
        ELABORATES: The subject statement expands on the object statement.
        CONTRASTS: The subject statement contrasts with the object statement.
        DEPENDS_ON: The subject statement logically depends on the object.
        CITES: The subject statement cites the object.
        MOTIVATES: The subject statement motivates the object.
    """

    SUPPORTED_BY = "supported_by"
    REFUTED_BY = "refuted_by"
    GENERATED_BY = "generated_by"
    USED = "used"
    DERIVED_FROM = "derived_from"
    ATTRIBUTED_TO = "attributed_to"
    REVIEWED_BY = "reviewed_by"
    RELATES_TO = "relates_to"
    # Discourse relations between statements (the article's logical flow).
    ELABORATES = "elaborates"
    CONTRASTS = "contrasts"
    DEPENDS_ON = "depends_on"
    CITES = "cites"
    MOTIVATES = "motivates"


def _utcnow() -> datetime:
    """Return the current time as a timezone-aware UTC datetime.

    Returns:
        The current moment in UTC.

    """
    return datetime.now(UTC)


@dataclass
class ProvenanceRelation:
    """A directed, typed edge between two provenance nodes.

    The edge reads subject → predicate → object, e.g.
    ``(claim, SUPPORTED_BY, evidence)``.

    Attributes:
        subject_type: The :class:`NodeType` of the source node.
        subject_id: The identifier of the source node.
        predicate: The relationship the edge expresses.
        object_type: The :class:`NodeType` of the target node.
        object_id: The identifier of the target node.
        id: Stable unique identifier for the edge. Generated as a UUID4 hex
            string if not supplied.
        created_at: Timezone-aware timestamp of when this edge was created
            (UTC).
        metadata: Arbitrary structured metadata about the relationship.
    """

    subject_type: NodeType
    subject_id: str
    predicate: ProvenancePredicate
    object_type: NodeType
    object_id: str
    id: str = field(default_factory=lambda: uuid4().hex)
    created_at: datetime = field(default_factory=_utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialise the edge to a JSON-compatible dictionary.

        Node types and the predicate render as their stable string tokens and
        the timestamp as an ISO 8601 string, giving a representation suitable
        for exchange with other tools and autonomous agents.

        Returns:
            A dictionary representation of the edge.

        """
        return {
            "id": self.id,
            "subject_type": self.subject_type.value,
            "subject_id": self.subject_id,
            "predicate": self.predicate.value,
            "object_type": self.object_type.value,
            "object_id": self.object_id,
            "created_at": self.created_at.isoformat(),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProvenanceRelation:
        """Reconstruct an edge from its dictionary representation.

        This is the inverse of :meth:`to_dict`. ``subject_type``,
        ``subject_id``, ``predicate``, ``object_type``, and ``object_id`` are
        required; any missing optional field falls back to its default.

        Args:
            data: A dictionary as produced by :meth:`to_dict`.

        Returns:
            The reconstructed edge.

        Raises:
            KeyError: If any required field is missing.

        """
        kwargs: dict[str, Any] = {
            "subject_type": NodeType(data["subject_type"]),
            "subject_id": data["subject_id"],
            "predicate": ProvenancePredicate(data["predicate"]),
            "object_type": NodeType(data["object_type"]),
            "object_id": data["object_id"],
        }
        if "id" in data:
            kwargs["id"] = data["id"]
        if data.get("created_at") is not None:
            kwargs["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("metadata") is not None:
            kwargs["metadata"] = dict(data["metadata"])
        return cls(**kwargs)
