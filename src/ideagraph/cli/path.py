# ruff: noqa: PLC0415
"""The ``ideagraph path`` command (shortest idea-edge path between statements)."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer


def path_command(
    root: Annotated[Path, typer.Argument(help="Library root directory.")],
    src: Annotated[str, typer.Argument(help="Source statement global id (article_id#node_id).")],
    dst: Annotated[str, typer.Argument(help="Target statement global id (article_id#node_id).")],
    max_depth: Annotated[int, typer.Option("--max-depth", help="Maximum path length to search.")] = 8,
    as_json: Annotated[bool, typer.Option("--json", help="Emit the path as JSON.")] = False,
    db: Annotated[Path | None, typer.Option("--db", help="Index database path.")] = None,
) -> None:
    """Find a shortest directed path of idea edges from one statement to another.

    Follows edges in their asserted direction, across articles, so you can trace
    how one idea leads to another. Exits non-zero if no path is found.

    Args:
        root: Library root directory.
        src: Source statement global id.
        dst: Target statement global id.
        max_depth: Maximum path length to search.
        as_json: Emit the path as JSON.
        db: Optional index database path.
    """
    import json as _json

    from ideagraph.cli._library import open_indexed

    lib = open_indexed(root, db)
    try:
        trail = lib.path(src, dst, max_depth=max_depth)
        resolved = [{"gid": g, "text": (h.text if (h := lib.get_statement(g)) else None)} for g in (trail or [])]
    finally:
        lib.close()

    if as_json:
        typer.echo(_json.dumps({"found": trail is not None, "path": resolved}, indent=2))
    elif trail is None:
        typer.echo(f"No path from {src} to {dst} within depth {max_depth}.", err=True)
    else:
        for step in resolved:
            text = f'  "{step["text"]}"' if step["text"] else ""
            typer.echo(f"{step['gid']}{text}")

    if trail is None:
        raise typer.Exit(code=1)
