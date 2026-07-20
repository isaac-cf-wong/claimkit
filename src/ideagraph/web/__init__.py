"""Optional web UI for exploring a ideagraph provenance graph.

Requires the ``web`` extra (``pip install ideagraph[web]``). The heavy import
(Flask) lives in :mod:`ideagraph.web.app`, imported lazily so the core package
stays dependency-light.
"""

from __future__ import annotations

from ideagraph.web.app import build_library_payload, build_payload, create_app

__all__ = ["build_library_payload", "build_payload", "create_app"]
