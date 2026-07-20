# ruff: noqa: PLC0415
"""The ``ideagraph gaps`` command (library-wide gaps and loose ends)."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer


def gaps_command(
    root: Annotated[Path, typer.Argument(help="Library root directory.")],
    as_json: Annotated[bool, typer.Option("--json", help="Emit results as JSON.")] = False,
    strict: Annotated[bool, typer.Option("--strict", help="Exit non-zero if any gap is found.")] = False,
    db: Annotated[Path | None, typer.Option("--db", help="Index database path.")] = None,
) -> None:
    """Report library-wide gaps: unsupported assertions and dangling references.

    Surfaces where the knowledge base is incomplete: asserting statements
    (claim/finding/result) still unresolved against evidence, and cross-article
    references whose target no longer exists.

    Args:
        root: Library root directory.
        as_json: Emit results as JSON.
        strict: Exit non-zero if any gap is found.
        db: Optional index database path.
    """
    import json as _json

    from ideagraph.cli._library import open_indexed

    with open_indexed(root, db) as lib:
        unsupported = lib.unsupported_assertions()
        dangling = lib.dangling_cross_references()

    if as_json:
        typer.echo(
            _json.dumps(
                {
                    "unsupported_assertions": [{"gid": h.gid, "stype": h.stype, "text": h.text} for h in unsupported],
                    "dangling_cross_references": [{"src": e.src_gid, "target": e.dst_gid} for e in dangling],
                },
                indent=2,
            )
        )
    else:
        typer.echo(f"Unsupported assertions ({len(unsupported)}):")
        for h in unsupported:
            typer.echo(f"  {h.gid}  [{h.stype}]  {h.text}")
        typer.echo(f"\nDangling cross-references ({len(dangling)}):")
        for e in dangling:
            typer.echo(f"  {e.src_gid} -{e.predicate}-> {e.dst_gid}")

    if strict and (unsupported or dangling):
        raise typer.Exit(code=1)
