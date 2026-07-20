# ruff: noqa: PLC0415
"""The ``ideagraph stale`` command."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer

if TYPE_CHECKING:
    from ideagraph.core import Evidence


def _make_resolver(base: Path):
    """Build a digest resolver that hashes evidence references as files.

    Each piece of evidence's ``reference`` is treated as a path (relative to
    ``base``). The file is hashed with the algorithm named in the evidence's
    recorded digest prefix (defaulting to sha256). Evidence without a recorded
    digest, or whose reference is not an existing file, resolves to ``None`` so
    it is never reported as changed.

    Args:
        base: Directory that relative references are resolved against.

    Returns:
        A callable mapping evidence to its current digest or ``None``.

    """
    from ideagraph.core import hash_file

    def _resolve(evidence: Evidence) -> str | None:
        if evidence.digest is None:
            return None
        algorithm = evidence.digest.split(":", 1)[0] if ":" in evidence.digest else "sha256"
        path = base / evidence.reference
        if not path.is_file():
            return None
        return hash_file(path, algorithm=algorithm)

    return _resolve


def stale_command(
    path: Annotated[Path, typer.Argument(help="Path to a provenance graph JSON file.")],
    base: Annotated[
        Path | None,
        typer.Option("--base", help="Directory to resolve evidence references against (default: cwd)."),
    ] = None,
    apply: Annotated[
        bool,
        typer.Option("--apply", help="Flip affected VALID claims to STALE and save the file."),
    ] = False,
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit results as JSON."),
    ] = False,
) -> None:
    """Report claims whose supporting artefacts have changed on disk.

    A claim is stale when a supporting artefact's current content no longer
    matches the digest recorded on its evidence.

    Args:
        path: Path to a graph JSON file produced by ideagraph.
        base: Directory that relative evidence references are resolved against.
        apply: If set, mark affected VALID claims STALE and persist the change.
        as_json: If set, print results as JSON.
    """
    import json
    from logging import getLogger

    from ideagraph.core import find_stale_claims, mark_stale_claims
    from ideagraph.persistence import load_graph, save_graph

    logger = getLogger("ideagraph")

    if not path.exists():
        typer.echo(f"No such file: {path}", err=True)
        raise typer.Exit(code=1)

    graph = load_graph(path)
    resolver = _make_resolver(base if base is not None else Path.cwd())

    affected = find_stale_claims(graph, resolver)
    marked: list[str] = []
    if apply:
        marked = [claim.id for claim in mark_stale_claims(graph, resolver)]
        save_graph(graph, path)
        logger.info("Marked %d claim(s) stale in %s", len(marked), path)

    if as_json:
        payload = {"stale": [c.id for c in affected]}
        if apply:
            payload["marked"] = marked
        typer.echo(json.dumps(payload, indent=2))
        return

    if not affected:
        typer.echo("No stale claims.")
        return

    for claim in affected:
        typer.echo(f"{claim.id}: supporting evidence has changed")
    if apply:
        typer.echo(f"Marked {len(marked)} claim(s) as stale.")
