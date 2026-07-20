# ruff: noqa: PLC0415
"""Shared helper for CLI commands that read the library index."""

from __future__ import annotations

from pathlib import Path

import typer


def open_indexed(root: Path, db: Path | None = None):
    """Open the library at ``root`` and refresh its index incrementally.

    Discovery commands call this so results reflect the current files without the
    user having to run ``index`` first; the refresh is incremental (only changed
    articles are re-read), so it is cheap.

    Args:
        root: Library root directory.
        db: Optional index database path.

    Returns:
        An open :class:`~ideagraph.library.Library` (the caller must close it).

    Raises:
        typer.Exit: If ``root`` does not exist.
    """
    from ideagraph.library import Library

    if not root.exists():
        typer.echo(f"No such directory: {root}", err=True)
        raise typer.Exit(code=1)
    lib = Library(root, db)
    lib.index()
    return lib
