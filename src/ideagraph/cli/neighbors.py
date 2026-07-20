# ruff: noqa: PLC0415
"""The ``ideagraph neighbors`` command (idea-graph navigation)."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer


def _render_edge(lib, edge, gid: str) -> str:
    """Render an edge relative to ``gid``, resolving the other endpoint's text."""
    other = edge.dst_gid if edge.src_gid == gid else edge.src_gid
    arrow = f"-{edge.predicate}->" if edge.src_gid == gid else f"<-{edge.predicate}-"
    hit = lib.get_statement(other)
    text = f'  "{hit.text}"' if hit else "  (not in library)"
    tag = "" if edge.kind == "intra" else " [cross]"
    return f"{arrow} {other}{tag}{text}"


def neighbors_command(
    root: Annotated[Path, typer.Argument(help="Library root directory.")],
    gid: Annotated[str, typer.Argument(help="Global id of the statement (article_id#node_id).")],
    direction: Annotated[
        str,
        typer.Option("--direction", help="Which edges to show: out, in, or both."),
    ] = "both",
    as_json: Annotated[bool, typer.Option("--json", help="Emit results as JSON.")] = False,
    db: Annotated[Path | None, typer.Option("--db", help="Index database path.")] = None,
) -> None:
    """List the idea-graph edges touching a statement.

    Shows discourse links within the statement's article and cross-article
    references, resolving each neighbour's text when it is in the library.

    Args:
        root: Library root directory.
        gid: The statement's global id.
        direction: ``out``, ``in``, or ``both``.
        as_json: Emit results as JSON.
        db: Optional index database path.
    """
    import json as _json

    from ideagraph.cli._library import open_indexed

    lib = open_indexed(root, db)
    try:
        edges = lib.neighbors(gid, direction=direction)
        if as_json:
            payload = [{"src": e.src_gid, "dst": e.dst_gid, "predicate": e.predicate, "kind": e.kind} for e in edges]
            typer.echo(_json.dumps(payload, indent=2))
            return
        typer.echo(gid)
        for e in edges:
            typer.echo("  " + _render_edge(lib, e, gid))
        typer.echo(f"\n{len(edges)} edge(s)")
    finally:
        lib.close()
