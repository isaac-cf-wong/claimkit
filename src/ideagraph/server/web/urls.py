"""URL configuration for the ideagraph web UI app."""

from __future__ import annotations

from django.urls import path

from ideagraph.server.web import views

app_name = "web"

urlpatterns = [
    path("", views.index, name="index"),
]
