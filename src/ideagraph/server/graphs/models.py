"""ORM models persisting ideagraph provenance graphs.

The models store each node/edge's serialised dataclass dict (``data``) as the
source of truth, alongside a few denormalised, indexed columns for querying and
display. Conversion to/from the in-memory
:class:`~ideagraph.core.graph.ProvenanceGraph` lives in :mod:`.bridge`.
"""

from __future__ import annotations

from django.db import models


class Graph(models.Model):
    """A stored provenance graph (one article's statements/evidence/edges)."""

    slug = models.SlugField(unique=True, max_length=200)
    article_id = models.CharField(max_length=200, blank=True, default="")
    title = models.CharField(max_length=500, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["slug"]

    def __str__(self) -> str:
        """Return the graph's title or slug."""
        return self.title or self.slug


class Node(models.Model):
    """A statement, evidence, or activity node within a graph."""

    class Kind(models.TextChoices):
        STATEMENT = "statement", "Statement"
        EVIDENCE = "evidence", "Evidence"
        ACTIVITY = "activity", "Activity"

    graph = models.ForeignKey(Graph, on_delete=models.CASCADE, related_name="nodes")
    node_id = models.CharField(max_length=200)
    kind = models.CharField(max_length=16, choices=Kind.choices)
    # Denormalised for querying/display; the authoritative copy is `data`.
    stype = models.CharField(max_length=32, blank=True, default="")
    status = models.CharField(max_length=32, blank=True, default="")
    text = models.TextField(blank=True, default="")
    data = models.JSONField()

    class Meta:
        ordering = ["graph", "kind", "node_id"]
        constraints = [
            models.UniqueConstraint(fields=["graph", "node_id"], name="uniq_node_per_graph"),
        ]
        indexes = [
            models.Index(fields=["graph", "kind"]),
            models.Index(fields=["graph", "status"]),
        ]

    def __str__(self) -> str:
        """Return a short label for the node."""
        return f"{self.kind}:{self.node_id}"


class Edge(models.Model):
    """A provenance relation or cross-article reference within a graph."""

    class EdgeClass(models.TextChoices):
        RELATION = "relation", "Relation"
        CROSS_REFERENCE = "cross_reference", "Cross reference"

    graph = models.ForeignKey(Graph, on_delete=models.CASCADE, related_name="edges")
    edge_id = models.CharField(max_length=200)
    edge_class = models.CharField(max_length=20, choices=EdgeClass.choices)
    subject_id = models.CharField(max_length=200)
    predicate = models.CharField(max_length=32)
    # object_id for a relation; the global target address for a cross reference.
    object_ref = models.CharField(max_length=400)
    subject_type = models.CharField(max_length=16, blank=True, default="")
    object_type = models.CharField(max_length=16, blank=True, default="")
    data = models.JSONField()

    class Meta:
        ordering = ["graph", "edge_class", "edge_id"]
        constraints = [
            models.UniqueConstraint(fields=["graph", "edge_id"], name="uniq_edge_per_graph"),
        ]
        indexes = [
            models.Index(fields=["graph", "subject_id"]),
            models.Index(fields=["graph", "object_ref"]),
        ]

    def __str__(self) -> str:
        """Return a short label for the edge."""
        return f"{self.subject_id} -{self.predicate}-> {self.object_ref}"
