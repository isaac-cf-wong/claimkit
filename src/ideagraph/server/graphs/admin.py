"""Django admin registration for the graphs app."""

from __future__ import annotations

from django.contrib import admin

from ideagraph.server.graphs.models import Edge, Graph, Node


@admin.register(Graph)
class GraphAdmin(admin.ModelAdmin):
    """Admin for stored graphs."""

    list_display = ("slug", "title", "article_id", "updated_at")
    search_fields = ("slug", "title", "article_id")


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    """Admin for graph nodes."""

    list_display = ("graph", "kind", "node_id", "stype", "status")
    list_filter = ("kind", "stype", "status")
    search_fields = ("node_id", "text")


@admin.register(Edge)
class EdgeAdmin(admin.ModelAdmin):
    """Admin for graph edges."""

    list_display = ("graph", "edge_class", "subject_id", "predicate", "object_ref")
    list_filter = ("edge_class", "predicate")
    search_fields = ("subject_id", "object_ref")
