"""Tests for the DRF graph API."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from ideagraph.core import (
    Evidence,
    EvidenceKind,
    NodeType,
    ProvenanceGraph,
    ProvenancePredicate,
    ProvenanceRelation,
    Statement,
    StatementType,
)
from ideagraph.server.graphs.bridge import graph_to_orm
from ideagraph.server.graphs.models import Graph, GraphCollaborator

User = get_user_model()


def _sample() -> ProvenanceGraph:
    """Build a small graph (claim supported by evidence)."""
    g = ProvenanceGraph(article_id="a", metadata={"title": "Demo"})
    g.add_statement(Statement(statement="A claim.", id="c1", type=StatementType.CLAIM))
    g.add_evidence(Evidence(claim_id="c1", kind=EvidenceKind.DATA, reference="d.csv", id="e1"))
    g.add_relation(
        ProvenanceRelation(
            subject_type=NodeType.CLAIM,
            subject_id="c1",
            predicate=ProvenancePredicate.SUPPORTED_BY,
            object_type=NodeType.EVIDENCE,
            object_id="e1",
            id="r1",
        )
    )
    return g


@pytest.fixture
def owner(db):
    """Create an owner user.

    Args:
        db: pytest-django database fixture.

    Returns:
        The owner user.

    """
    return User.objects.create_user("owner", password="x")


def test_requires_authentication():
    """Unauthenticated API access is rejected."""
    assert APIClient().get("/api/graphs/").status_code in (401, 403)


def test_list_shows_only_visible(owner):
    """The list is scoped to the user's visible graphs."""
    graph_to_orm(_sample(), slug="mine", owner=owner)
    other = User.objects.create_user("other", password="x")
    graph_to_orm(_sample(), slug="theirs", owner=other)
    client = APIClient()
    client.force_authenticate(owner)
    slugs = {g["slug"] for g in client.get("/api/graphs/").json()}
    assert slugs == {"mine"}


def test_create_graph_from_content(owner):
    """POSTing {slug, content} creates a graph owned by the requester."""
    client = APIClient()
    client.force_authenticate(owner)
    resp = client.post("/api/graphs/", {"slug": "new", "content": _sample().to_dict()}, format="json")
    assert resp.status_code == 201
    graph = Graph.objects.get(slug="new")
    assert graph.owner_id == owner.pk
    assert graph.nodes.count() == 2


def test_create_conflict(owner):
    """Creating a duplicate slug returns 409."""
    graph_to_orm(_sample(), slug="dup", owner=owner)
    client = APIClient()
    client.force_authenticate(owner)
    resp = client.post("/api/graphs/", {"slug": "dup", "content": _sample().to_dict()}, format="json")
    assert resp.status_code == 409


def test_content_export_roundtrips(owner):
    """The content action returns a graph that round-trips to the original."""
    graph_to_orm(_sample(), slug="mine", owner=owner)
    client = APIClient()
    client.force_authenticate(owner)
    data = client.get("/api/graphs/mine/content/").json()
    restored = ProvenanceGraph.from_dict(data)
    assert set(restored.statements) == {"c1"}
    assert set(restored.evidence) == {"e1"}
    assert set(restored.relations) == {"r1"}


def test_payload_action(owner):
    """The payload action returns the visualization payload."""
    graph_to_orm(_sample(), slug="mine", owner=owner)
    client = APIClient()
    client.force_authenticate(owner)
    data = client.get("/api/graphs/mine/payload/").json()
    assert data["counts"] == {"statements": 1, "evidence": 1, "activities": 0}


def test_read_collaborator_cannot_write(owner):
    """A read collaborator may GET but not PUT or DELETE."""
    graph_to_orm(_sample(), slug="mine", owner=owner)
    reader = User.objects.create_user("reader", password="x")
    GraphCollaborator.objects.create(
        graph=Graph.objects.get(slug="mine"), user=reader, role=GraphCollaborator.Role.READ
    )
    client = APIClient()
    client.force_authenticate(reader)
    assert client.get("/api/graphs/mine/").status_code == 200
    assert client.put("/api/graphs/mine/", {"content": _sample().to_dict()}, format="json").status_code == 403
    assert client.delete("/api/graphs/mine/").status_code == 403


def test_write_collaborator_can_replace(owner):
    """A write collaborator may replace a graph's content."""
    graph_to_orm(_sample(), slug="mine", owner=owner)
    writer = User.objects.create_user("writer", password="x")
    GraphCollaborator.objects.create(
        graph=Graph.objects.get(slug="mine"), user=writer, role=GraphCollaborator.Role.WRITE
    )
    smaller = ProvenanceGraph(article_id="a")
    smaller.add_statement(Statement(statement="Only one.", id="c1"))
    client = APIClient()
    client.force_authenticate(writer)
    resp = client.put("/api/graphs/mine/", {"content": smaller.to_dict()}, format="json")
    assert resp.status_code == 200
    assert Graph.objects.get(slug="mine").nodes.count() == 1


def test_token_auth(owner):
    """A token obtained from the auth endpoint authorises API calls."""
    token = Token.objects.create(user=owner)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    assert client.get("/api/graphs/").status_code == 200


def test_obtain_token_endpoint(owner):
    """The token endpoint issues a token for valid credentials."""
    resp = APIClient().post("/api/auth/token/", {"username": "owner", "password": "x"}, format="json")
    assert resp.status_code == 200
    assert "token" in resp.json()
