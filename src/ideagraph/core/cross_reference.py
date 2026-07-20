"""Cross-article edges: a statement in this article pointing at one in another.

A :class:`CrossReference` is the mechanism behind use case 3 (connecting
articles). When this article's statement cites, builds on, or contradicts an idea
in another article, that link is recorded here — in the *asserting* article's
graph — as ``subject_id --predicate--> target``, where ``target`` is a global
address (:func:`~ideagraph.core.identity.global_id`) into the other article.

The edge lives with the article that makes the claim, so there is one source of
truth per link and the other article need not be edited. Whether the target
actually resolves to a real statement is a *library-level* question (the other
graph must be present): the single-article ``doctor`` checks only that the
subject is local and the target is well-formed; full resolution happens once the
library index can see every graph.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from ideagraph.core.identity import parse_global_id
from ideagraph.core.provenance import ProvenancePredicate


def _utcnow() -> datetime:
    """Return the current time as a timezone-aware UTC datetime.

    Returns:
        The current moment in UTC.
    """
    return datetime.now(UTC)


@dataclass
class CrossReference:
    """A directed edge from a local statement to a statement in another article.

    Reads ``subject_id → predicate → target``, e.g.
    ``("c1", CITES, "goncharov2022#f3")``.

    Attributes:
        subject_id: The local statement id this edge starts from.
        predicate: The relationship the edge expresses (typically ``cites``,
            ``builds_on``, ``extends``, ``contradicts``, or ``same_as``).
        target: The global address ``article_id#node_id`` of the statement in
            the other article.
        id: Stable unique identifier for the edge (UUID4 hex if not supplied).
        created_at: Timezone-aware creation timestamp (UTC).
        metadata: Arbitrary structured metadata about the link.
    """

    subject_id: str
    predicate: ProvenancePredicate
    target: str
    id: str = field(default_factory=lambda: uuid4().hex)
    created_at: datetime = field(default_factory=_utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def target_article(self) -> str:
        """The article id of the target (raises ValueError if malformed)."""
        return parse_global_id(self.target)[0]

    @property
    def target_node(self) -> str:
        """The node id of the target (raises ValueError if malformed)."""
        return parse_global_id(self.target)[1]

    def to_dict(self) -> dict[str, Any]:
        """Serialise the cross-reference to a JSON-compatible dictionary.

        Returns:
            A dictionary representation of the edge.
        """
        return {
            "id": self.id,
            "subject_id": self.subject_id,
            "predicate": self.predicate.value,
            "target": self.target,
            "created_at": self.created_at.isoformat(),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CrossReference:
        """Reconstruct a cross-reference from its dictionary representation.

        Args:
            data: A dictionary as produced by :meth:`to_dict`. ``subject_id``,
                ``predicate``, and ``target`` are required.

        Returns:
            The reconstructed cross-reference.

        Raises:
            KeyError: If any required field is missing.
        """
        kwargs: dict[str, Any] = {
            "subject_id": data["subject_id"],
            "predicate": ProvenancePredicate(data["predicate"]),
            "target": data["target"],
        }
        if "id" in data:
            kwargs["id"] = data["id"]
        if data.get("created_at") is not None:
            kwargs["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("metadata") is not None:
            kwargs["metadata"] = dict(data["metadata"])
        return cls(**kwargs)
