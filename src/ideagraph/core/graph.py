"""The :class:`ProvenanceGraph`, an in-memory aggregate of nodes and edges.

The individual models — :class:`~ideagraph.core.claim.Claim`,
:class:`~ideagraph.core.evidence.Evidence`,
:class:`~ideagraph.core.activity.Activity` — and the typed
:class:`~ideagraph.core.provenance.ProvenanceRelation` edges between them are
independent and serialisable on their own. This module ties them together into
a single container that indexes nodes by id and supports directed traversal, so
that both humans and autonomous agents can ask questions such as "what evidence
supports this claim?" or "what did this activity generate?".

The graph is deliberately permissive: an edge may reference an endpoint that is
not held as a node (for example an artefact or agent, which have no dedicated
node model yet). Such dangling references are preserved rather than rejected, so
provenance can be recorded incrementally and completed later.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from ideagraph.core.activity import Activity
from ideagraph.core.cross_reference import CrossReference
from ideagraph.core.evidence import Evidence
from ideagraph.core.identity import global_id as _global_id
from ideagraph.core.provenance import NodeType, ProvenancePredicate, ProvenanceRelation
from ideagraph.core.statement import Statement, StatementType


@dataclass
class ProvenanceGraph:
    """An in-memory collection of provenance nodes and the edges between them.

    Nodes are stored by :attr:`~ideagraph.core.claim.Claim.id`, keeping the most
    recently added node for a given id. Edges are stored in insertion order and
    indexed by both endpoints for constant-time traversal.

    Attributes:
        statements: Statements held by the graph, keyed by id (a claim is the
            ``StatementType.CLAIM`` case).
        evidence: Evidence held by the graph, keyed by id.
        activities: Activities held by the graph, keyed by id.
        relations: Intra-article edges held by the graph, keyed by id.
        cross_references: Cross-article edges (this article -> another), keyed
            by id.
        article_id: This graph's stable article id. Statements are addressed
            globally as ``article_id#node_id``; required before another article
            can reference this one, and before this article can point outward
            with a resolvable back-reference.
        metadata: Arbitrary graph-level metadata (e.g. ``title``).
    """

    statements: dict[str, Statement] = field(default_factory=dict)
    evidence: dict[str, Evidence] = field(default_factory=dict)
    activities: dict[str, Activity] = field(default_factory=dict)
    relations: dict[str, ProvenanceRelation] = field(default_factory=dict)
    cross_references: dict[str, CrossReference] = field(default_factory=dict)
    article_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    _out: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list), repr=False, compare=False)
    _in: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list), repr=False, compare=False)

    @property
    def claims(self) -> dict[str, Statement]:
        """Claim-typed statements, keyed by id (backward-compatible view)."""
        return {sid: s for sid, s in self.statements.items() if s.type is StatementType.CLAIM}

    def add_statement(self, statement: Statement) -> Statement:
        """Add or replace a statement.

        Args:
            statement: The statement to store.

        Returns:
            The stored statement.
        """
        self.statements[statement.id] = statement
        return statement

    def add_claim(self, claim: Statement) -> Statement:
        """Add or replace a statement (backward-compatible alias for add_statement).

        Args:
            claim: The statement to store.

        Returns:
            The stored statement.
        """
        return self.add_statement(claim)

    def add_cross_reference(self, cross_reference: CrossReference) -> CrossReference:
        """Add or replace a cross-article edge.

        Args:
            cross_reference: The cross-article edge to store.

        Returns:
            The stored cross-article edge.
        """
        self.cross_references[cross_reference.id] = cross_reference
        return cross_reference

    def global_id(self, node_id: str) -> str:
        """Return the global address ``article_id#node_id`` for a local node.

        Args:
            node_id: A local statement id.

        Returns:
            The global address.

        Raises:
            ValueError: If this graph has no ``article_id`` set, or the id is
                malformed.
        """
        if self.article_id is None:
            raise ValueError("graph has no article_id; set one before building global ids")
        return _global_id(self.article_id, node_id)

    def add_evidence(self, evidence: Evidence) -> Evidence:
        """Add or replace a piece of evidence.

        Args:
            evidence: The evidence to store.

        Returns:
            The stored evidence.

        """
        self.evidence[evidence.id] = evidence
        return evidence

    def add_activity(self, activity: Activity) -> Activity:
        """Add or replace an activity.

        Args:
            activity: The activity to store.

        Returns:
            The stored activity.

        """
        self.activities[activity.id] = activity
        return activity

    def add_relation(self, relation: ProvenanceRelation) -> ProvenanceRelation:
        """Add or replace a provenance edge and update the traversal index.

        Args:
            relation: The edge to store.

        Returns:
            The stored edge.

        """
        if relation.id in self.relations:
            self._deindex(self.relations[relation.id])
        self.relations[relation.id] = relation
        self._out[relation.subject_id].append(relation.id)
        self._in[relation.object_id].append(relation.id)
        return relation

    def _deindex(self, relation: ProvenanceRelation) -> None:
        """Remove an edge from the traversal index.

        Args:
            relation: The edge to remove from the index.

        """
        out_ids = self._out.get(relation.subject_id)
        if out_ids and relation.id in out_ids:
            out_ids.remove(relation.id)
        in_ids = self._in.get(relation.object_id)
        if in_ids and relation.id in in_ids:
            in_ids.remove(relation.id)

    def outgoing(self, node_id: str, predicate: ProvenancePredicate | None = None) -> list[ProvenanceRelation]:
        """Return edges whose subject is ``node_id``.

        Args:
            node_id: The id of the source node.
            predicate: If given, only edges with this predicate are returned.

        Returns:
            The matching edges, in insertion order.

        """
        edges = [self.relations[rid] for rid in self._out.get(node_id, [])]
        if predicate is not None:
            edges = [e for e in edges if e.predicate is predicate]
        return edges

    def incoming(self, node_id: str, predicate: ProvenancePredicate | None = None) -> list[ProvenanceRelation]:
        """Return edges whose object is ``node_id``.

        Args:
            node_id: The id of the target node.
            predicate: If given, only edges with this predicate are returned.

        Returns:
            The matching edges, in insertion order.

        """
        edges = [self.relations[rid] for rid in self._in.get(node_id, [])]
        if predicate is not None:
            edges = [e for e in edges if e.predicate is predicate]
        return edges

    def evidence_for(self, claim_id: str) -> list[Evidence]:
        """Return evidence linked to a claim by a supports/refutes edge.

        Only edges whose object is a piece of evidence held by the graph are
        followed; dangling references are skipped.

        Args:
            claim_id: The id of the claim.

        Returns:
            The linked evidence held by the graph, in edge insertion order.

        """
        result: list[Evidence] = []
        for edge in self.outgoing(claim_id):
            if edge.predicate not in (ProvenancePredicate.SUPPORTED_BY, ProvenancePredicate.REFUTED_BY):
                continue
            if edge.object_type is NodeType.EVIDENCE and edge.object_id in self.evidence:
                result.append(self.evidence[edge.object_id])
        return result

    def to_dict(self) -> dict[str, Any]:
        """Serialise the whole graph to a JSON-compatible dictionary.

        Returns:
            A dictionary with ``statements``, ``evidence``, ``activities``, and
            ``relations`` lists, each element produced by the corresponding
            model's ``to_dict``.

        """
        return {
            "article_id": self.article_id,
            "metadata": dict(self.metadata),
            "statements": [s.to_dict() for s in self.statements.values()],
            "evidence": [e.to_dict() for e in self.evidence.values()],
            "activities": [a.to_dict() for a in self.activities.values()],
            "relations": [r.to_dict() for r in self.relations.values()],
            "cross_references": [x.to_dict() for x in self.cross_references.values()],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProvenanceGraph:
        """Reconstruct a graph from its dictionary representation.

        This is the inverse of :meth:`to_dict`. Missing collections are treated
        as empty.

        Args:
            data: A dictionary as produced by :meth:`to_dict`.

        Returns:
            The reconstructed graph, with its traversal index rebuilt.

        """
        graph = cls()
        graph.article_id = data.get("article_id")
        if data.get("metadata") is not None:
            graph.metadata = dict(data["metadata"])
        # v-next reads "statements"; pre-v-next graphs stored them under "claims".
        for s in data.get("statements", data.get("claims", [])):
            graph.add_statement(Statement.from_dict(s))
        for e in data.get("evidence", []):
            graph.add_evidence(Evidence.from_dict(e))
        for a in data.get("activities", []):
            graph.add_activity(Activity.from_dict(a))
        for r in data.get("relations", []):
            graph.add_relation(ProvenanceRelation.from_dict(r))
        for x in data.get("cross_references", []):
            graph.add_cross_reference(CrossReference.from_dict(x))
        return graph
