# ruff: noqa: PLC0415
"""Shared helper for CLI commands that read the library index."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import typer


@contextmanager
def open_indexed(root: Path, db: Path | None = None) -> Iterator:
    """Open the library at ``root``, refresh it incrementally, and yield it.

    Discovery commands use this so results reflect the current files without the
    user having to run ``index`` first; the refresh is incremental (only changed
    articles are re-read), so it is cheap. The library is closed on exit.

    Args:
        root: Library root directory.
        db: Optional index database path.

    Yields:
        An open :class:`~ideagraph.library.Library`.

    Raises:
        typer.Exit: If ``root`` does not exist.
    """
    from ideagraph.library import Library

    if not root.exists():
        typer.echo(f"No such directory: {root}", err=True)
        raise typer.Exit(code=1)
    with Library(root, db) as lib:
        lib.index()
        yield lib
