"""The ideagraph Django web interface.

This package hosts the Django project (settings, URL configuration, WSGI/ASGI
entry points) and the Django apps that serve the web UI and API. The graph
engine itself lives in the sibling ``ideagraph`` modules (``core``,
``persistence``, ``library``, …) and is reused here rather than reimplemented.
"""

from __future__ import annotations
