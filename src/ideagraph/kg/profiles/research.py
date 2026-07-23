"""The built-in ``research`` profile and its vocabulary.

Reproduces the scientific-provenance vocabulary of the original ideagraph as a
knowledge-graph profile: statement node types (claim, finding, …) plus evidence
and activity nodes, and the provenance / discourse / cross-article edge types
with their endpoint constraints.

The vocabulary enums here are the single source of truth: they drive both the
profile's rules and the CLI option choices, and the string-set constants
(``STATEMENT_TYPES``, ``ASSERTION_TYPES``, …) are derived from them.
"""

from __future__ import annotations

import enum

from ideagraph.kg.profile import EdgeRule, NodeRule, Profile, register_profile


class StatementType(enum.StrEnum):
    """The rhetorical role a statement node plays."""

    CLAIM = "claim"
    FINDING = "finding"
    BACKGROUND = "background"
    METHOD = "method"
    DEFINITION = "definition"
    MOTIVATION = "motivation"
    RESULT = "result"
    OTHER = "other"


class StatementStatus(enum.StrEnum):
    """Validation status of an assertion statement."""

    UNRESOLVED = "unresolved"
    VALID = "valid"
    STALE = "stale"
    INVALID = "invalid"
    NEEDS_REVIEW = "needs_review"


class EvidenceKind(enum.StrEnum):
    """The type of artefact a piece of evidence points at."""

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
    """How a piece of evidence bears on a claim."""

    SUPPORTS = "supports"
    REFUTES = "refutes"
    CONTEXTUAL = "contextual"


class ActivityKind(enum.StrEnum):
    """The type of process an activity represents."""

    COMPUTATION = "computation"
    MEASUREMENT = "measurement"
    ANALYSIS = "analysis"
    REVIEW = "review"
    IMPORT = "import"
    OTHER = "other"


class NodeType(enum.StrEnum):
    """The category of a node for relation-endpoint reasoning."""

    CLAIM = "claim"
    EVIDENCE = "evidence"
    ACTIVITY = "activity"
    ARTEFACT = "artefact"
    AGENT = "agent"


class ProvenancePredicate(enum.StrEnum):
    """The vocabulary of edge types in the research profile."""

    SUPPORTED_BY = "supported_by"
    REFUTED_BY = "refuted_by"
    GENERATED_BY = "generated_by"
    USED = "used"
    DERIVED_FROM = "derived_from"
    ATTRIBUTED_TO = "attributed_to"
    REVIEWED_BY = "reviewed_by"
    RELATES_TO = "relates_to"
    ELABORATES = "elaborates"
    CONTRASTS = "contrasts"
    DEPENDS_ON = "depends_on"
    CITES = "cites"
    MOTIVATES = "motivates"
    BUILDS_ON = "builds_on"
    EXTENDS = "extends"
    CONTRADICTS = "contradicts"
    SAME_AS = "same_as"


# ClaimStatus is a backward-compatible alias of StatementStatus.
ClaimStatus = StatementStatus

#: Statement node types (rhetorical roles), as plain strings.
STATEMENT_TYPES = tuple(t.value for t in StatementType)

#: Statement types that assert something and therefore require support.
ASSERTION_TYPES = frozenset({StatementType.CLAIM.value, StatementType.FINDING.value, StatementType.RESULT.value})

#: Discourse edge types (statement -> statement rhetorical links).
DISCOURSE_TYPES = frozenset(
    {
        ProvenancePredicate.ELABORATES.value,
        ProvenancePredicate.CONTRASTS.value,
        ProvenancePredicate.DEPENDS_ON.value,
        ProvenancePredicate.CITES.value,
        ProvenancePredicate.MOTIVATES.value,
    }
)

#: Cross-article edge types (this article -> another).
CROSS_ARTICLE_TYPES = frozenset(
    {
        ProvenancePredicate.BUILDS_ON.value,
        ProvenancePredicate.EXTENDS.value,
        ProvenancePredicate.CONTRADICTS.value,
        ProvenancePredicate.SAME_AS.value,
    }
)

_EVIDENCE = "evidence"
_ACTIVITY = "activity"
_STATEMENT_SET = frozenset(STATEMENT_TYPES)


def _build_profile() -> Profile:
    """Construct the research profile.

    Returns:
        The research profile.

    """
    node_types = {t: NodeRule(t) for t in STATEMENT_TYPES}
    node_types[_EVIDENCE] = NodeRule(_EVIDENCE, required_properties=frozenset({"kind", "reference"}))
    node_types[_ACTIVITY] = NodeRule(_ACTIVITY, required_properties=frozenset({"label"}))

    edge_types: dict[str, EdgeRule] = {
        "supported_by": EdgeRule("supported_by", source_types=_STATEMENT_SET, target_types=frozenset({_EVIDENCE})),
        "refuted_by": EdgeRule("refuted_by", source_types=_STATEMENT_SET, target_types=frozenset({_EVIDENCE})),
        "generated_by": EdgeRule("generated_by", target_types=frozenset({_ACTIVITY})),
        "used": EdgeRule("used", source_types=frozenset({_ACTIVITY})),
        "derived_from": EdgeRule("derived_from"),
        "attributed_to": EdgeRule("attributed_to"),
        "reviewed_by": EdgeRule("reviewed_by"),
        "relates_to": EdgeRule("relates_to"),
    }
    for t in DISCOURSE_TYPES:
        edge_types[t] = EdgeRule(t, source_types=_STATEMENT_SET, target_types=_STATEMENT_SET)
    for t in CROSS_ARTICLE_TYPES:
        edge_types[t] = EdgeRule(t, source_types=_STATEMENT_SET)
    return Profile(name="research", node_types=node_types, edge_types=edge_types)


RESEARCH = register_profile(_build_profile())
