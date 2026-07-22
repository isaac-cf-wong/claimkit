"""Views for the ideagraph web UI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from ideagraph.server.graphs.permissions import visible_graphs
from ideagraph.version import __version__

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


def index(request: HttpRequest) -> HttpResponse:
    """Render the landing page.

    Args:
        request: The incoming request.

    Returns:
        The rendered landing page.

    """
    return render(request, "web/index.html", {"page": "home", "version": __version__})


def _role_for(user: object, graph: object) -> str:
    """Return a display label for a user's role on a graph.

    Args:
        user: The requesting user.
        graph: The graph being listed.

    Returns:
        One of ``owner``, ``read``, ``write``, or ``admin`` (superuser).

    """
    if graph.owner_id == user.pk:
        return "owner"
    membership = graph.collaborators.filter(user=user).first()
    if membership is not None:
        return membership.role
    return "admin" if user.is_superuser else "—"


@login_required
def graphs_list(request: HttpRequest) -> HttpResponse:
    """List the graphs the signed-in user may view, with their role.

    Args:
        request: The incoming request.

    Returns:
        The rendered graph list.

    """
    graphs = visible_graphs(request.user).select_related("owner").prefetch_related("collaborators")
    rows = [{"graph": g, "role": _role_for(request.user, g)} for g in graphs]
    return render(request, "web/graphs_list.html", {"page": "graphs", "rows": rows})
