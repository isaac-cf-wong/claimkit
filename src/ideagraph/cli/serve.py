# ruff: noqa: PLC0415
"""The ``ideagraph serve`` command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer


def serve_command(
    path: Annotated[Path, typer.Argument(help="Path to a provenance graph JSON file.")],
    host: Annotated[str, typer.Option("--host", help="Interface to bind.")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", help="Port to listen on.")] = 8000,
    base: Annotated[
        Path | None,
        typer.Option("--base", help="Directory relative evidence references resolve against (default: graph dir)."),
    ] = None,
    doc: Annotated[
        list[Path] | None,
        typer.Option("--doc", help="A LaTeX/Markdown draft to show with inline provenance. Repeatable."),
    ] = None,
    bib: Annotated[
        Path | None,
        typer.Option("--bib", help="A BibTeX file to label literature evidence (citation keys -> titles)."),
    ] = None,
) -> None:
    r"""Serve an interactive provenance web UI for a graph.

    Opens a local web app showing the claim/evidence/activity graph coloured by
    each claim's live status (valid / invalid / stale / unresolved), with a
    click-through detail panel. Status is recomputed from disk on every request,
    so editing the graph or a referenced artefact is reflected on refresh.

    With ``--doc`` the app also serves a Document tab: the draft rendered as a
    reading view where each ``\\prov{id}{...}`` (LaTeX) / ``[...](prov:id)``
    (Markdown) mark is highlighted by its provenance status and links to the
    node, so the source of every number/statement is visible while reading.

    Requires the ``web`` extra: ``pip install ideagraph[web]``.

    Args:
        path: Path to a graph JSON file produced by ideagraph.
        host: Interface to bind the server to.
        port: Port to listen on.
        base: Directory relative evidence references resolve against.
        doc: Draft files (LaTeX/Markdown) to expose in the Document tab.
        bib: A BibTeX file to label literature evidence with citation titles.
    """
    from logging import getLogger

    logger = getLogger("ideagraph")

    if not path.exists():
        typer.echo(f"No such file: {path}", err=True)
        raise typer.Exit(code=1)

    try:
        from ideagraph.web import create_app
    except ModuleNotFoundError:
        typer.echo("The web UI needs Flask; install it with `pip install ideagraph[web]`.", err=True)
        raise typer.Exit(code=1) from None

    for d in doc or []:
        if not d.exists():
            typer.echo(f"No such document: {d}", err=True)
            raise typer.Exit(code=1)
    bib_entries = None
    if bib is not None:
        if not bib.exists():
            typer.echo(f"No such bib file: {bib}", err=True)
            raise typer.Exit(code=1)
        from ideagraph.bib import parse_bibtex

        bib_entries = parse_bibtex(bib)
    app = create_app(path, base, docs=list(doc or []), bib=bib_entries)
    logger.info("Serving provenance for %s at http://%s:%d", path, host, port)
    typer.echo(f"ideagraph provenance UI -> http://{host}:{port}  (Ctrl-C to stop)")
    app.run(host=host, port=port)
