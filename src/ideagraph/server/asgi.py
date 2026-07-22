"""ASGI entry point for the ideagraph web interface."""

from __future__ import annotations

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ideagraph.server.settings")

application = get_asgi_application()
