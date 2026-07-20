# ruff: noqa: PLC0415
"""The ``ideagraph find`` command (full-text search across the library)."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer


def find_command(
    root: Annotated[Path, typer.Argument(help="Library root directory to search.")],
    query: Annotated[str, typer.Argument(help="Free-text search terms.")],
    stype: Annotated[
        str | None,
        typer.Option("--type", help="Only show statements of this rhetorical type (e.g. claim, finding)."),
    ] = None,
    limit: Annotated[int, typer.Option("--limit", help="Maximum number of hits.")] = 20,
    as_json: Annotated[bool, typer.Option("--json", help="Emit results as JSON.")] = False,
    db: Annotated[Path | None, typer.Option("--db", help="Index database path.")] = None,
) -> None:
    """Search statement text across every article in the library.

    Args:
        root: Library root directory.
        query: Free-text search terms.
        stype: Optional rhetorical-type filter.
        limit: Maximum number of hits.
        as_json: Emit results as JSON.
        db: Optional index database path.
    """
    import json as _json

    from ideagraph.cli._library import open_indexed

    lib = open_indexed(root, db)
    try:
        hits = [h for h in lib.search(query, limit=limit) if stype is None or h.stype == stype]
    finally:
        lib.close()

    if as_json:
        typer.echo(
            _json.dumps(
                [{"gid": h.gid, "stype": h.stype, "text": h.text} for h in hits],
                indent=2,
            )
        )
        return
    for h in hits:
        typer.echo(f"{h.gid}  [{h.stype}]  {h.text}")
    typer.echo(f"\n{len(hits)} hit(s)")
