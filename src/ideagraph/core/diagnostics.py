"""Integrity checks for a graph — the engine behind ``ideagraph doctor``.

:func:`diagnose` walks a graph and reports problems that would otherwise surface
only as silent dangling edges: a cross-reference from a statement that does not
exist, a malformed global target, an intra-article edge pointing at a missing
node, or outward links from a graph that has no ``article_id`` (so nothing can
point back at it).

Cross-article *resolution* — does the target ``article_id#node_id`` actually
exist? — needs every graph in view and is therefore a library-level check. Pass
``known_articles`` (the set of article ids the library holds) to enable the
"unknown article" warning; without it, single-graph ``doctor`` only checks the
address is well-formed and, for self-references, that the local node exists.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ideagraph.core.identity import is_global_id, parse_global_id
from ideagraph.core.provenance import NodeType

if TYPE_CHECKING:
    from ideagraph.core.graph import ProvenanceGraph

#: Diagnostic levels, most severe first.
_LEVEL_ORDER = {"error": 0, "warning": 1, "info": 2}


@dataclass(frozen=True)
class Diagnostic:
    """A single problem found in a graph.

    Attributes:
        level: ``"error"``, ``"warning"``, or ``"info"``.
        code: A stable machine-readable slug (e.g. ``xref-dangling-subject``).
        message: A human-readable description.
        ref: The id of the offending node/edge, if applicable.
    """

    level: str
    code: str
    message: str
    ref: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        """Serialise the diagnostic to a JSON-compatible dictionary."""
        return {"level": self.level, "code": self.code, "message": self.message, "ref": self.ref}


def _node_missing(graph: ProvenanceGraph, node_type: NodeType, node_id: str) -> bool:
    """Whether a typed intra-article endpoint refers to a node not held.

    Artefact and agent endpoints are intentionally allowed to dangle (they have
    no node model yet), so they are never reported.
    """
    if node_type is NodeType.CLAIM:
        return node_id not in graph.statements
    if node_type is NodeType.EVIDENCE:
        return node_id not in graph.evidence
    if node_type is NodeType.ACTIVITY:
        return node_id not in graph.activities
    return False


def diagnose(graph: ProvenanceGraph, *, known_articles: Iterable[str] | None = None) -> list[Diagnostic]:
    """Report integrity problems in a graph, most severe first.

    Args:
        graph: The graph to check.
        known_articles: If given, the set of article ids the library holds;
            cross-references whose target article is outside this set are
            flagged ``xref-unknown-article``. Omit for a single-graph check.

    Returns:
        The diagnostics found, sorted error → warning → info.
    """
    known = set(known_articles) if known_articles is not None else None
    out: list[Diagnostic] = []

    if graph.cross_references and graph.article_id is None:
        out.append(
            Diagnostic(
                "warning",
                "no-article-id",
                "graph has cross-references but no article_id, so no other article can point back at it",
            )
        )

    for xref in graph.cross_references.values():
        if xref.subject_id not in graph.statements:
            out.append(
                Diagnostic(
                    "error",
                    "xref-dangling-subject",
                    f"cross-reference subject {xref.subject_id!r} is not a statement in this graph",
                    xref.id,
                )
            )
        if not is_global_id(xref.target):
            out.append(
                Diagnostic(
                    "error",
                    "xref-bad-target",
                    f"cross-reference target {xref.target!r} is not a valid 'article_id#node_id' address",
                    xref.id,
                )
            )
            continue
        target_article, target_node = parse_global_id(xref.target)
        if target_article == graph.article_id and target_node not in graph.statements:
            out.append(
                Diagnostic(
                    "error",
                    "xref-self-dangling",
                    f"cross-reference target {xref.target!r} points into this article at a missing node",
                    xref.id,
                )
            )
        elif known is not None and target_article not in known:
            out.append(
                Diagnostic(
                    "warning",
                    "xref-unknown-article",
                    f"cross-reference target article {target_article!r} is not in the library",
                    xref.id,
                )
            )

    for rel in graph.relations.values():
        if _node_missing(graph, rel.subject_type, rel.subject_id):
            out.append(
                Diagnostic(
                    "warning",
                    "relation-dangling-subject",
                    f"relation subject {rel.subject_id!r} ({rel.subject_type.value}) is not held by the graph",
                    rel.id,
                )
            )
        if _node_missing(graph, rel.object_type, rel.object_id):
            out.append(
                Diagnostic(
                    "warning",
                    "relation-dangling-object",
                    f"relation object {rel.object_id!r} ({rel.object_type.value}) is not held by the graph",
                    rel.id,
                )
            )

    out.sort(key=lambda d: _LEVEL_ORDER.get(d.level, 99))
    return out
