"""App configuration for the graphs (ORM persistence) app."""

from __future__ import annotations

from django.apps import AppConfig


class GraphsConfig(AppConfig):
    """Configuration for the graphs app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "ideagraph.server.graphs"
    label = "graphs"
