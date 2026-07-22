"""Foundation tests for the ideagraph Django web interface."""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse


def test_index_renders():
    """The landing page renders with the ideagraph branding."""
    response = Client().get(reverse("web:index"))
    assert response.status_code == 200
    body = response.content.decode()
    assert "ideagraph" in body
    assert "navigable graph" in body


def test_index_url_is_root():
    """The web index is mounted at the site root."""
    assert reverse("web:index") == "/"


@pytest.mark.django_db
def test_admin_login_redirect():
    """The admin is wired up and redirects anonymous users to log in."""
    response = Client().get("/admin/")
    assert response.status_code == 302
    assert "/admin/login/" in response.headers["Location"]
