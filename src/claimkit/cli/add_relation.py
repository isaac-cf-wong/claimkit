# ruff: noqa: PLC0415
"""The ``claimkit add-relation`` command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from claimkit.core import NodeType, ProvenancePredicate

#: Node types claimkit stores and can therefore verify an id against. ARTEFACT
#: and AGENT nodes are not held in the graph (they appear only as relation
#: endpoints), so an id of those types is accepted without an existence check.
_STORED_TYPES = (NodeType.CLAIM, NodeType.EVIDENCE, NodeType.ACTIVITY)


def _detect_type(graph, node_id: str) -> NodeType | None:
    """Infer a stored node's type from its id, or None if not found/ambiguous.

    Args:
        graph: The provenance graph to search.
        node_id: The id to look up.

    Returns:
        The node's :class:`NodeType`, or None if no stored node has that id.
    """
    found = [
        node_type
        for node_type, store in (
            (NodeType.CLAIM, graph.claims),
            (NodeType.EVIDENCE, graph.evidence),
            (NodeType.ACTIVITY, graph.activities),
        )
        if node_id in store
    ]
    return found[0] if len(found) == 1 else None


def _resolve_type(graph, node_id: str, explicit: NodeType | None, role: str) -> NodeType:
    """Resolve a node's type from an explicit flag or by detection.

    Args:
        graph: The provenance graph.
        node_id: The node id.
        explicit: A type passed on the command line, or None to auto-detect.
        role: ``"subject"`` or ``"object"``, for error messages.

    Returns:
        The resolved :class:`NodeType`.

    Raises:
        typer.Exit: If the type cannot be resolved or the stored node is absent.
    """
    node_type = explicit or _detect_type(graph, node_id)
    if node_type is None:
        typer.echo(
            f"Cannot determine {role} type for {node_id!r}; pass --{role}-type "
            f"(no stored claim/evidence/activity has that id).",
            err=True,
        )
        raise typer.Exit(code=1)
    if node_type in _STORED_TYPES:
        store = {
            NodeType.CLAIM: graph.claims,
            NodeType.EVIDENCE: graph.evidence,
            NodeType.ACTIVITY: graph.activities,
        }[node_type]
        if node_id not in store:
            typer.echo(f"No such {node_type.value}: {node_id}", err=True)
            raise typer.Exit(code=1)
    return node_type


def add_relation_command(
    path: Annotated[Path, typer.Argument(help="Path to a provenance graph JSON file.")],
    subject_id: Annotated[str, typer.Argument(help="Id of the subject (source) node.")],
    object_id: Annotated[str, typer.Argument(help="Id of the object (target) node.")],
    predicate: Annotated[
        ProvenancePredicate,
        typer.Option("--predicate", help="The typed relationship from subject to object."),
    ],
    subject_type: Annotated[
        NodeType | None,
        typer.Option("--subject-type", help="Subject node type (auto-detected if omitted)."),
    ] = None,
    object_type: Annotated[
        NodeType | None,
        typer.Option("--object-type", help="Object node type (auto-detected if omitted)."),
    ] = None,
) -> None:
    """Add a typed provenance edge between two nodes and print its id.

    The subject/object types are auto-detected from their ids when the nodes are
    stored in the graph (claims, evidence, activities); pass ``--subject-type`` /
    ``--object-type`` for artefact or agent endpoints, which the graph does not
    store. Examples: link evidence to the activity that produced it
    (``--predicate generated_by``), or attach existing evidence to a second
    claim (``--predicate supported_by``).

    Args:
        path: Path to a graph JSON file produced by claimkit.
        subject_id: Id of the subject (source) node.
        object_id: Id of the object (target) node.
        predicate: The typed relationship from subject to object.
        subject_type: Explicit subject type, or None to auto-detect.
        object_type: Explicit object type, or None to auto-detect.
    """
    from logging import getLogger

    from claimkit.core import ProvenanceRelation
    from claimkit.persistence import load_graph, save_graph

    logger = getLogger("claimkit")

    if not path.exists():
        typer.echo(f"No such file: {path}", err=True)
        raise typer.Exit(code=1)

    graph = load_graph(path)
    subj_type = _resolve_type(graph, subject_id, subject_type, "subject")
    obj_type = _resolve_type(graph, object_id, object_type, "object")

    relation = ProvenanceRelation(
        subject_type=subj_type,
        subject_id=subject_id,
        predicate=predicate,
        object_type=obj_type,
        object_id=object_id,
    )
    graph.add_relation(relation)
    save_graph(graph, path)

    logger.info(
        "Added relation %s: %s %s %s",
        relation.id,
        subject_id,
        predicate.value,
        object_id,
    )
    typer.echo(relation.id)
