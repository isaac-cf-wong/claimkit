# ruff: noqa: PLC0415
"""The ``ideagraph backlinks`` command (who references an idea)."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer


def backlinks_command(
    root: Annotated[Path, typer.Argument(help="Library root directory.")],
    gid: Annotated[str, typer.Argument(help="Global id of the statement (article_id#node_id).")],
    as_json: Annotated[bool, typer.Option("--json", help="Emit results as JSON.")] = False,
    db: Annotated[Path | None, typer.Option("--db", help="Index database path.")] = None,
) -> None:
    """List statements that point *at* a statement — its incoming references.

    Answers "which ideas, here or in other articles, build on / cite / contrast
    this one?". Cross-article backlinks are the basis of a citation map.

    Args:
        root: Library root directory.
        gid: The statement's global id.
        as_json: Emit results as JSON.
        db: Optional index database path.
    """
    import json as _json

    from ideagraph.cli._library import open_indexed

    with open_indexed(root, db) as lib:
        edges = lib.backlinks(gid)
        if as_json:
            payload = [
                {"src": e.src_gid, "predicate": e.predicate, "kind": e.kind, "article_id": e.article_id} for e in edges
            ]
            typer.echo(_json.dumps(payload, indent=2))
            return
        typer.echo(f"backlinks to {gid}:")
        for e in edges:
            hit = lib.get_statement(e.src_gid)
            text = f'  "{hit.text}"' if hit else ""
            tag = "" if e.kind == "intra" else " [cross]"
            typer.echo(f"  {e.src_gid} -{e.predicate}->{tag}{text}")
        typer.echo(f"\n{len(edges)} backlink(s)")
