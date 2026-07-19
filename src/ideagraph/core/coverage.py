"""Support coverage: is each claim backed by evidence, and of what origin?

A claim is *supported* when at least one ``SUPPORTED_BY`` edge links it to
evidence the graph holds. The supporting evidence is classified by origin:

* **own** — first-hand/empirical evidence produced by this work
  (``code``/``data``/``workflow``/``figure``/``table``/``instrument``);
* **literature** — a citation (``literature``);
* **other** — anything else (``environment``/``human_review``/``other``).

This turns "does every statement have support from the literature or from our
own findings?" into a checkable report: unsupported claims are the gaps.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ideagraph.core.evidence import EvidenceKind
from ideagraph.core.graph import ProvenanceGraph
from ideagraph.core.provenance import NodeType, ProvenancePredicate
from ideagraph.core.statement import ASSERTION_TYPES, StatementType

#: Evidence kinds counting as the authors' own first-hand support.
_OWN_KINDS = frozenset(
    {
        EvidenceKind.CODE,
        EvidenceKind.DATA,
        EvidenceKind.WORKFLOW,
        EvidenceKind.FIGURE,
        EvidenceKind.TABLE,
        EvidenceKind.INSTRUMENT,
    }
)


@dataclass
class ClaimCoverage:
    """How (and whether) a single claim is supported.

    Attributes:
        claim_id: The claim's id.
        has_own: Whether it has first-hand supporting evidence.
        has_literature: Whether it has literature (citation) support.
        has_other: Whether it has other supporting evidence.
        evidence_kinds: The kinds of all supporting evidence, de-duplicated.
    """

    claim_id: str
    has_own: bool = False
    has_literature: bool = False
    has_other: bool = False
    evidence_kinds: list[str] = field(default_factory=list)

    @property
    def supported(self) -> bool:
        """Whether the claim has any supporting evidence."""
        return self.has_own or self.has_literature or self.has_other

    @property
    def category(self) -> str:
        """A single label: ``unsupported`` / ``own`` / ``literature`` / ``both`` / ``other``."""
        if not self.supported:
            return "unsupported"
        if self.has_own and self.has_literature:
            return "both"
        if self.has_literature:
            return "literature"
        if self.has_own:
            return "own"
        return "other"

    def to_dict(self) -> dict:
        """Serialise to a JSON-compatible dict."""
        return {
            "claim_id": self.claim_id,
            "category": self.category,
            "supported": self.supported,
            "has_own": self.has_own,
            "has_literature": self.has_literature,
            "has_other": self.has_other,
            "evidence_kinds": list(self.evidence_kinds),
        }


def claim_coverage(graph: ProvenanceGraph, claim_id: str) -> ClaimCoverage:
    """Classify one claim's support origin from its ``SUPPORTED_BY`` evidence.

    Args:
        graph: The provenance graph.
        claim_id: The claim to classify.

    Returns:
        Its :class:`ClaimCoverage`.
    """
    cov = ClaimCoverage(claim_id=claim_id)
    kinds: list[EvidenceKind] = []
    for rel in graph.outgoing(claim_id):
        if rel.predicate is not ProvenancePredicate.SUPPORTED_BY or rel.object_type is not NodeType.EVIDENCE:
            continue
        ev = graph.evidence.get(rel.object_id)
        if ev is None:
            continue
        if ev.kind not in kinds:
            kinds.append(ev.kind)
        if ev.kind is EvidenceKind.LITERATURE:
            cov.has_literature = True
        elif ev.kind in _OWN_KINDS:
            cov.has_own = True
        else:
            cov.has_other = True
    cov.evidence_kinds = [k.value for k in kinds]
    return cov


def coverage(graph: ProvenanceGraph, types: frozenset[StatementType] = ASSERTION_TYPES) -> dict[str, ClaimCoverage]:
    """Classify support coverage for every asserting statement in the graph.

    Only statements whose type is in ``types`` (by default claim / finding /
    result) are checked — these are the ones that require support; background,
    method, definition, and motivation may carry support but are not gaps when
    they lack it.

    Args:
        graph: The provenance graph.
        types: The statement types to include (default: the assertion types).

    Returns:
        A mapping of statement id to its :class:`ClaimCoverage`.
    """
    return {sid: claim_coverage(graph, sid) for sid, s in graph.statements.items() if s.type in types}
