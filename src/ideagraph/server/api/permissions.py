"""DRF permission class enforcing per-graph access.

Reuses the same :mod:`ideagraph.server.graphs.permissions` helpers the web
views use, so the API and the UI can never diverge on who may read or write a
graph.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework.permissions import SAFE_METHODS, BasePermission

from ideagraph.server.graphs.permissions import can_edit, can_view

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.views import APIView

    from ideagraph.server.graphs.models import Graph


class GraphPermission(BasePermission):
    """Allow safe methods to viewers and unsafe methods to editors."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Require an authenticated user for any API access.

        Args:
            request: The incoming request.
            view: The view being accessed.

        Returns:
            ``True`` if the user is authenticated.

        """
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request: Request, view: APIView, obj: Graph) -> bool:
        """Gate object access: view for safe methods, edit otherwise.

        Args:
            request: The incoming request.
            view: The view being accessed.
            obj: The graph being accessed.

        Returns:
            ``True`` if the user may perform the request on the graph.

        """
        if request.method in SAFE_METHODS:
            return can_view(request.user, obj)
        return can_edit(request.user, obj)
