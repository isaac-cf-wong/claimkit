"""Convert between stored ORM rows and the in-memory ProvenanceGraph.

The engine's :class:`~ideagraph.core.graph.ProvenanceGraph` already serialises to
and from plain dicts. This bridge stores those per-node/per-edge dicts in the
ORM (with denormalised columns) and reconstructs the graph from them, so the
domain model is reused rather than duplicated.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.db import transaction

from ideagraph.core.graph import ProvenanceGraph
from ideagraph.server.graphs.models import Edge, Graph, Node

if TYPE_CHECKING:
    from collections.abc import Iterable

_NODE_SECTIONS = (
    ("statements", Node.Kind.STATEMENT),
    ("evidence", Node.Kind.EVIDENCE),
    ("activities", Node.Kind.ACTIVITY),
)


def _node_rows(graph: Graph, sections: dict[str, Any]) -> Iterable[Node]:
    """Yield Node rows for a graph from a serialised graph dict.

    Args:
        graph: The owning Graph row.
        sections: A ``ProvenanceGraph.to_dict()`` mapping.

    Yields:
        Unsaved Node instances.

    """
    for key, kind in _NODE_SECTIONS:
        for item in sections.get(key, []):
            if kind is Node.Kind.STATEMENT:
                text, stype, status = item.get("statement", ""), item.get("type", ""), item.get("status", "")
            elif kind is Node.Kind.EVIDENCE:
                text, stype, status = item.get("reference", ""), "", ""
            else:
                text, stype, status = item.get("label", ""), "", ""
            yield Node(
                graph=graph,
                node_id=item["id"],
                kind=kind,
                stype=stype or "",
                status=status or "",
                text=text or "",
                data=item,
            )


def _edge_rows(graph: Graph, sections: dict[str, Any]) -> Iterable[Edge]:
    """Yield Edge rows for a graph from a serialised graph dict.

    Args:
        graph: The owning Graph row.
        sections: A ``ProvenanceGraph.to_dict()`` mapping.

    Yields:
        Unsaved Edge instances.

    """
    for item in sections.get("relations", []):
        yield Edge(
            graph=graph,
            edge_id=item["id"],
            edge_class=Edge.EdgeClass.RELATION,
            subject_id=item["subject_id"],
            predicate=item["predicate"],
            object_ref=item["object_id"],
            subject_type=item.get("subject_type", ""),
            object_type=item.get("object_type", ""),
            data=item,
        )
    for item in sections.get("cross_references", []):
        yield Edge(
            graph=graph,
            edge_id=item["id"],
            edge_class=Edge.EdgeClass.CROSS_REFERENCE,
            subject_id=item["subject_id"],
            predicate=item["predicate"],
            object_ref=item["target"],
            data=item,
        )


@transaction.atomic
def graph_to_orm(pg: ProvenanceGraph, *, slug: str, owner: object = None) -> Graph:
    """Persist a ProvenanceGraph as a Graph row (replacing any existing one).

    Args:
        pg: The in-memory graph to store.
        slug: The stable URL/slug identifier for the stored graph.
        owner: Optional user to record as the graph's owner.

    Returns:
        The saved Graph row.

    """
    sections = pg.to_dict()
    Graph.objects.filter(slug=slug).delete()
    graph = Graph.objects.create(
        slug=slug,
        article_id=pg.article_id or "",
        title=str(pg.metadata.get("title", "")) if pg.metadata else "",
        metadata=dict(pg.metadata),
        owner=owner,
    )
    Node.objects.bulk_create(list(_node_rows(graph, sections)))
    Edge.objects.bulk_create(list(_edge_rows(graph, sections)))
    return graph


def orm_to_graph(graph: Graph) -> ProvenanceGraph:
    """Reconstruct a ProvenanceGraph from a stored Graph row.

    Args:
        graph: The Graph row to read.

    Returns:
        The reconstructed in-memory graph.

    """
    nodes = list(graph.nodes.all())
    edges = list(graph.edges.all())
    data = {
        "article_id": graph.article_id or None,
        "metadata": dict(graph.metadata),
        "statements": [n.data for n in nodes if n.kind == Node.Kind.STATEMENT],
        "evidence": [n.data for n in nodes if n.kind == Node.Kind.EVIDENCE],
        "activities": [n.data for n in nodes if n.kind == Node.Kind.ACTIVITY],
        "relations": [e.data for e in edges if e.edge_class == Edge.EdgeClass.RELATION],
        "cross_references": [e.data for e in edges if e.edge_class == Edge.EdgeClass.CROSS_REFERENCE],
    }
    return ProvenanceGraph.from_dict(data)
