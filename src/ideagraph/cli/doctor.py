# ruff: noqa: PLC0415
"""The ``ideagraph doctor`` command (graph integrity report)."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer


def doctor_command(
    path: Annotated[Path, typer.Argument(help="Path to a provenance graph JSON file.")],
    as_json: Annotated[bool, typer.Option("--json", help="Emit diagnostics as JSON.")] = False,
    strict: Annotated[
        bool,
        typer.Option("--strict", help="Exit non-zero on warnings too, not just errors."),
    ] = False,
) -> None:
    """Check a graph's integrity and report problems.

    Flags cross-references from missing statements, malformed global targets,
    self-references into missing local nodes, intra-article edges pointing at
    absent nodes, and outward links from a graph with no ``article_id``. Exits
    non-zero if any error is found (or any warning, with ``--strict``).

    Cross-article target *resolution* (does ``article_id#node_id`` exist in
    another article?) is a library-level check and is not performed here.

    Args:
        path: Path to a graph JSON file produced by ideagraph.
        as_json: Emit the diagnostics as JSON.
        strict: Treat warnings as failures too.
    """
    import json as _json
    from logging import getLogger

    from ideagraph.core import diagnose
    from ideagraph.persistence import load_graph

    logger = getLogger("ideagraph")

    if not path.exists():
        typer.echo(f"No such file: {path}", err=True)
        raise typer.Exit(code=1)

    diagnostics = diagnose(load_graph(path))
    errors = [d for d in diagnostics if d.level == "error"]
    warnings = [d for d in diagnostics if d.level == "warning"]

    if as_json:
        typer.echo(_json.dumps([d.to_dict() for d in diagnostics], indent=2))
    elif not diagnostics:
        typer.echo("No problems found.")
    else:
        for d in diagnostics:
            ref = f" [{d.ref}]" if d.ref else ""
            typer.echo(f"{d.level.upper()}: {d.code}: {d.message}{ref}")
        typer.echo(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")

    logger.info("doctor: %d error(s), %d warning(s) in %s", len(errors), len(warnings), path)
    if errors or (strict and warnings):
        raise typer.Exit(code=1)
