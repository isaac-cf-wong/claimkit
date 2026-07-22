"""Tests for per-graph permissions and the auth-gated graph list."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from ideagraph.server.graphs.models import Graph, GraphCollaborator
from ideagraph.server.graphs.permissions import can_edit, can_view, visible_graphs

User = get_user_model()


@pytest.fixture
def users(db):
    """Create an owner, a reader, a writer, an outsider, and a superuser.

    Args:
        db: pytest-django database fixture.

    Returns:
        A dict of created users.

    """
    return {
        "owner": User.objects.create_user("owner", password="x"),
        "reader": User.objects.create_user("reader", password="x"),
        "writer": User.objects.create_user("writer", password="x"),
        "outsider": User.objects.create_user("outsider", password="x"),
        "admin": User.objects.create_superuser("admin", password="x"),
    }


@pytest.fixture
def graph(users):
    """Create a graph owned by ``owner`` with a reader and a writer.

    Args:
        users: The users fixture.

    Returns:
        The graph.

    """
    g = Graph.objects.create(slug="demo", title="Demo", owner=users["owner"])
    GraphCollaborator.objects.create(graph=g, user=users["reader"], role=GraphCollaborator.Role.READ)
    GraphCollaborator.objects.create(graph=g, user=users["writer"], role=GraphCollaborator.Role.WRITE)
    return g


def test_can_view(users, graph):
    """Owner, collaborators, and superuser can view; outsider cannot."""
    assert can_view(users["owner"], graph)
    assert can_view(users["reader"], graph)
    assert can_view(users["writer"], graph)
    assert can_view(users["admin"], graph)
    assert not can_view(users["outsider"], graph)


def test_can_edit(users, graph):
    """Owner, write collaborator, and superuser can edit; reader cannot."""
    assert can_edit(users["owner"], graph)
    assert can_edit(users["writer"], graph)
    assert can_edit(users["admin"], graph)
    assert not can_edit(users["reader"], graph)
    assert not can_edit(users["outsider"], graph)


def test_visible_graphs_filtering(users, graph):
    """visible_graphs returns only graphs a user may see."""
    assert list(visible_graphs(users["owner"])) == [graph]
    assert list(visible_graphs(users["reader"])) == [graph]
    assert list(visible_graphs(users["outsider"])) == []
    assert list(visible_graphs(users["admin"])) == [graph]


def test_visible_graphs_anonymous():
    """An anonymous user sees no graphs."""
    from django.contrib.auth.models import AnonymousUser

    assert list(visible_graphs(AnonymousUser())) == []


@pytest.mark.django_db
def test_graphs_list_requires_login():
    """The graph list redirects anonymous users to the login page."""
    response = Client().get(reverse("web:graphs"))
    assert response.status_code == 302
    assert reverse("login") in response.headers["Location"]


def test_graphs_list_shows_only_visible(users, graph):
    """The list shows a user's graphs and their role, hiding others'."""
    other = Graph.objects.create(slug="secret", title="Secret", owner=users["outsider"])
    client = Client()
    client.force_login(users["reader"])
    body = client.get(reverse("web:graphs")).content.decode()
    assert "Demo" in body
    assert "read" in body
    assert "Secret" not in body
    assert other.slug not in body


def test_login_flow(users):
    """A user can sign in through the login form."""
    client = Client()
    response = client.post(reverse("login"), {"username": "owner", "password": "x"})
    assert response.status_code == 302
    assert client.get(reverse("web:graphs")).status_code == 200
