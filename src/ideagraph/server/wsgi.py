"""WSGI entry point for the ideagraph web interface."""

from __future__ import annotations

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ideagraph.server.settings")

application = get_wsgi_application()
