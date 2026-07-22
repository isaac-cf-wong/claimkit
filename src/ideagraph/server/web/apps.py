"""App configuration for the ideagraph web UI."""

from __future__ import annotations

from django.apps import AppConfig


class WebConfig(AppConfig):
    """Configuration for the ideagraph web UI app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "ideagraph.server.web"
    label = "web"
