#!/usr/bin/env python
"""Django management entry point for the ideagraph web interface."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> None:
    """Run administrative tasks."""
    # src-layout: make the `ideagraph` package importable without installation.
    src = Path(__file__).resolve().parent / "src"
    if src.is_dir() and str(src) not in sys.path:
        sys.path.insert(0, str(src))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ideagraph.server.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:  # pragma: no cover - import guard
        raise ImportError("Django is not installed. Install the web extra: `pip install ideagraph[web]`.") from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
