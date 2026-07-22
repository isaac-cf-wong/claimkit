"""Views for the ideagraph web UI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.shortcuts import render

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
