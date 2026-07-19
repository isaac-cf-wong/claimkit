"""Saving and loading a :class:`~claimkit.core.graph.ProvenanceGraph` as JSON.

The graph and its nodes already serialise to plain dictionaries; this module
adds a stable on-disk envelope around that representation. Each document is
wrapped with a ``schema_version`` so the format can evolve while older files
stay loadable, giving both humans and autonomous agents a durable, diffable
interchange format for provenance.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from claimkit.core.graph import ProvenanceGraph

#: Current on-disk schema version. Bump when the envelope or the underlying
#: graph representation changes in a way that affects loading.
SCHEMA_VERSION = 2  # v2: claims -> statements (typed); pre-v2 "claims" still read


def graph_to_document(graph: ProvenanceGraph) -> dict[str, Any]:
    """Wrap a graph's serialised form in a versioned envelope.

    Args:
        graph: The graph to wrap.

    Returns:
        A dictionary with ``schema_version`` and ``graph`` keys.

    """
    return {"schema_version": SCHEMA_VERSION, "graph": graph.to_dict()}


def graph_from_document(document: dict[str, Any]) -> ProvenanceGraph:
    """Reconstruct a graph from a versioned envelope.

    Args:
        document: A dictionary as produced by :func:`graph_to_document`.

    Returns:
        The reconstructed graph.

    Raises:
        KeyError: If the envelope is missing ``schema_version`` or ``graph``.
        ValueError: If the ``schema_version`` is newer than this library
            supports.

    """
    version = document["schema_version"]
    if version > SCHEMA_VERSION:
        raise ValueError(
            f"document schema_version {version} is newer than supported version {SCHEMA_VERSION}; "
            "upgrade claimkit to read it"
        )
    return ProvenanceGraph.from_dict(document["graph"])


def dumps_graph(graph: ProvenanceGraph, *, indent: int = 2) -> str:
    """Serialise a graph to a JSON string.

    Args:
        graph: The graph to serialise.
        indent: Indentation passed to :func:`json.dumps`.

    Returns:
        The JSON document as a string.

    """
    return json.dumps(graph_to_document(graph), indent=indent, ensure_ascii=False)


def loads_graph(text: str) -> ProvenanceGraph:
    """Deserialise a graph from a JSON string.

    Args:
        text: A JSON document as produced by :func:`dumps_graph`.

    Returns:
        The reconstructed graph.

    Raises:
        ValueError: If the ``schema_version`` is unsupported.

    """
    return graph_from_document(json.loads(text))


def save_graph(graph: ProvenanceGraph, path: str | Path, *, indent: int = 2) -> None:
    """Write a graph to a JSON file, creating parent directories as needed.

    A trailing newline is appended so the file plays well with text tooling.

    Args:
        graph: The graph to save.
        path: Destination file path.
        indent: Indentation passed to :func:`json.dumps`.

    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(dumps_graph(graph, indent=indent) + "\n", encoding="utf-8")


def load_graph(path: str | Path) -> ProvenanceGraph:
    """Read a graph from a JSON file.

    Args:
        path: Source file path.

    Returns:
        The reconstructed graph.

    Raises:
        ValueError: If the ``schema_version`` is unsupported.

    """
    return loads_graph(Path(path).read_text(encoding="utf-8"))
