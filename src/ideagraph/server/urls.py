"""Root URL configuration for the ideagraph web interface."""

from __future__ import annotations

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("api/", include("ideagraph.server.api.urls")),
    path("", include("ideagraph.server.web.urls")),
]
