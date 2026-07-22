"""URL configuration for the graph API."""

from __future__ import annotations

from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from ideagraph.server.api.views import GraphViewSet

app_name = "api"

router = DefaultRouter()
router.register("graphs", GraphViewSet, basename="graph")

urlpatterns = [
    path("auth/token/", obtain_auth_token, name="token"),
    *router.urls,
]
