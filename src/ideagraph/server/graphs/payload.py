"""Build the front-end JSON payload for a stored graph.

Reconstructs the in-memory :class:`~ideagraph.core.graph.ProvenanceGraph` from an
ORM row and computes the same node/edge shape the visualization expects, reusing
the engine's validation and coverage. Staleness (which needs the referenced
artefact files on disk) is not computed for the hosted store; the CLI ``stale``
command covers that for local graphs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ideagraph import EvidenceKind, coverage, validate_all
from ideagraph.bib import format_citation
from ideagraph.server.graphs.bridge import orm_to_graph
from ideagraph.server.graphs.models import Edge, Node

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from ideagraph.server.graphs.models import Graph

_DISCOURSE = {"elaborates", "contrasts", "depends_on", "cites", "motivates"}


def _article_key(graph: Graph) -> str:
    """Return the article key used to namespace a graph's node ids.

    Args:
        graph: The graph.

    Returns:
        The graph's ``article_id`` if set, else its slug.

    """
    return graph.article_id or graph.slug


def library_payload(graphs: QuerySet[Graph]) -> dict[str, Any]:
    """Aggregate several graphs into one cross-article idea-graph payload.

    Nodes are every statement across the given graphs (grouped/coloured by
    article); edges are intra-article discourse links and cross-article
    references. A cross reference whose target statement is absent from the set
    is flagged ``dangling``.

    Args:
        graphs: The graphs to aggregate (typically the viewer's visible graphs).

    Returns:
        A dict with ``articles``, ``nodes``, ``edges``, and ``counts`` — the
        shape the library view's JavaScript consumes.

    """
    graphs = graphs.prefetch_related("nodes", "edges")
    articles: list[dict[str, str]] = []
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    for graph in graphs:
        art = _article_key(graph)
        articles.append({"id": art, "title": graph.title or graph.slug})
        statement_ids = set()
        for node in graph.nodes.all():
            if node.kind != Node.Kind.STATEMENT:
                continue
            statement_ids.add(node.node_id)
            nodes.append(
                {
                    "id": f"{art}#{node.node_id}",
                    "article": art,
                    "node": node.node_id,
                    "stype": node.stype,
                    "status": node.status,
                    "text": node.text,
                }
            )
        for edge in graph.edges.all():
            if (
                edge.edge_class == Edge.EdgeClass.RELATION
                and edge.predicate in _DISCOURSE
                and edge.subject_id in statement_ids
                and edge.object_ref in statement_ids
            ):
                edges.append(
                    {
                        "source": f"{art}#{edge.subject_id}",
                        "target": f"{art}#{edge.object_ref}",
                        "predicate": edge.predicate,
                        "kind": "intra",
                        "dangling": False,
                    }
                )
            elif edge.edge_class == Edge.EdgeClass.CROSS_REFERENCE:
                edges.append(
                    {
                        "source": f"{art}#{edge.subject_id}",
                        "target": edge.object_ref,
                        "predicate": edge.predicate,
                        "kind": "cross",
                        "dangling": False,
                    }
                )

    known = {n["id"] for n in nodes}
    for edge in edges:
        if edge["kind"] == "cross":
            edge["dangling"] = edge["target"] not in known

    return {
        "articles": articles,
        "nodes": nodes,
        "edges": edges,
        "counts": {
            "articles": len(articles),
            "statements": len(nodes),
            "cross_edges": sum(1 for e in edges if e["kind"] == "cross"),
        },
    }


def graph_payload(graph_row: Graph) -> dict[str, Any]:
    """Compute the visualization payload for a stored graph.

    Args:
        graph_row: The Graph ORM row to render.

    Returns:
        A dict with ``nodes``, ``edges``, ``summary`` (support coverage counts),
        and ``counts`` — the same shape the graph view's JavaScript consumes.

    """
    graph = orm_to_graph(graph_row)
    verdicts = validate_all(graph)
    cov = coverage(graph)

    nodes: list[dict[str, Any]] = []
    for sid, s in graph.statements.items():
        assertion = sid in cov
        nodes.append(
            {
                "id": sid,
                "type": "statement",
                "stype": s.type.value,
                "level": 0,
                "label": sid,
                "order": s.order,
                "section": s.section,
                "status": verdicts[sid].status.value if sid in verdicts else None,
                "support": cov[sid].category if assertion else None,
                "source_digest": s.source_digest,
                "statement": s.statement,
                "tags": list(s.tags),
                "metadata": s.metadata,
            }
        )
    for eid, ev in graph.evidence.items():
        is_lit = ev.kind is EvidenceKind.LITERATURE
        citation = format_citation(ev.reference, None) if is_lit else None
        nodes.append(
            {
                "id": eid,
                "type": "evidence",
                "level": 1,
                "label": citation if is_lit else eid,
                "status": "literature" if is_lit else "evidence",
                "kind": ev.kind.value,
                "reference": ev.reference,
                "citation": citation,
                "digest": ev.digest,
                "metadata": ev.metadata,
            }
        )
    for aid, act in graph.activities.items():
        nodes.append(
            {
                "id": aid,
                "type": "activity",
                "level": 2,
                "label": act.label,
                "status": "activity",
                "kind": act.kind.value,
                "metadata": act.metadata,
            }
        )

    edges = [
        {
            "source": rel.subject_id,
            "target": rel.object_id,
            "predicate": rel.predicate.value,
            "discourse": rel.predicate.value in _DISCOURSE,
        }
        for rel in graph.relations.values()
    ]

    summary: dict[str, int] = {}
    for c in cov.values():
        summary[c.category] = summary.get(c.category, 0) + 1

    return {
        "nodes": nodes,
        "edges": edges,
        "summary": summary,
        "counts": {
            "statements": len(graph.statements),
            "evidence": len(graph.evidence),
            "activities": len(graph.activities),
        },
    }
