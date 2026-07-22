"""Per-graph access rules: owner + read/write collaborators.

A graph is private to its owner and the collaborators explicitly granted access.
Superusers may see and edit everything. These helpers are the single place the
web views and (later) the API consult, so the rules cannot drift between them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Q

from ideagraph.server.graphs.models import Graph, GraphCollaborator

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
    from django.db.models import QuerySet

    User = AbstractBaseUser | AnonymousUser


def visible_graphs(user: User) -> QuerySet[Graph]:
    """Return the graphs a user may view.

    Args:
        user: The requesting user (may be anonymous).

    Returns:
        A queryset of graphs the user owns or collaborates on (all graphs for a
        superuser; none for an anonymous user).

    """
    if not user.is_authenticated:
        return Graph.objects.none()
    if user.is_superuser:
        return Graph.objects.all()
    return Graph.objects.filter(Q(owner=user) | Q(collaborators__user=user)).distinct()


def can_view(user: User, graph: Graph) -> bool:
    """Report whether a user may view a graph.

    Args:
        user: The requesting user.
        graph: The graph in question.

    Returns:
        ``True`` if the user owns, collaborates on, or (as superuser) may see
        the graph.

    """
    if not user.is_authenticated:
        return False
    if user.is_superuser or graph.owner_id == user.pk:
        return True
    return graph.collaborators.filter(user=user).exists()


def can_edit(user: User, graph: Graph) -> bool:
    """Report whether a user may modify a graph.

    Args:
        user: The requesting user.
        graph: The graph in question.

    Returns:
        ``True`` if the user is a superuser, the owner, or a write collaborator.

    """
    if not user.is_authenticated:
        return False
    if user.is_superuser or graph.owner_id == user.pk:
        return True
    return graph.collaborators.filter(user=user, role=GraphCollaborator.Role.WRITE).exists()
