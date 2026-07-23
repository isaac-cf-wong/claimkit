"""Tests for induced-subgraph extraction (ideagraph.kg.extract)."""

from __future__ import annotations

from ideagraph.kg import Edge, KnowledgeGraph, Node, extract_subgraph, find_stale_imports
from ideagraph.kg.extract import SOURCE_GID_KEY, SOURCE_HASH_KEY, neighbourhood


def _chain() -> KnowledgeGraph:
    """Return a->b->c->d chain plus a cross-article edge leaving a.

    Returns:
        A source graph with article_id ``src``.

    """
    g = KnowledgeGraph(article_id="src")
    for nid in ("a", "b", "c", "d"):
        g.add_node(Node(type="claim", id=nid, text=nid.upper()))
    g.add_edge(Edge(type="depends_on", source="a", target="b", id="ab"))
    g.add_edge(Edge(type="depends_on", source="b", target="c", id="bc"))
    g.add_edge(Edge(type="depends_on", source="c", target="d", id="cd"))
    g.add_edge(Edge(type="cites", source="a", target="other#x", id="ax"))
    return g


def test_neighbourhood_expands_both_directions():
    """Expansion follows edges either way and honours the hop budget."""
    g = _chain()
    assert neighbourhood(g, {"b"}, hops=0) == {"b"}
    assert neighbourhood(g, {"b"}, hops=1) == {"a", "b", "c"}
    assert neighbourhood(g, {"a"}, hops=2) == {"a", "b", "c"}


def test_neighbourhood_ignores_unknown_seeds():
    """Seed ids absent from the graph are dropped, not errored."""
    g = _chain()
    assert neighbourhood(g, {"a", "ghost"}, hops=0) == {"a"}


def test_extract_keeps_internal_and_cross_article_edges():
    """Internal edges among kept nodes and cross-article edges leaving them survive."""
    g = _chain()
    sub = extract_subgraph(g, {"a"}, hops=1)
    assert set(sub.nodes) == {"a", "b"}
    edge_ids = set(sub.edges)
    assert "ab" in edge_ids  # internal edge kept
    assert "ax" in edge_ids  # cross-article edge leaving a kept
    assert "bc" not in edge_ids  # c is out of the induced set


def test_extract_stamps_provenance():
    """Each copied node records its origin global id and text hash, once."""
    g = _chain()
    sub = extract_subgraph(g, {"a"}, hops=0)
    assert sub.nodes["a"].properties[SOURCE_GID_KEY] == "src#a"
    assert sub.nodes["a"].properties[SOURCE_HASH_KEY]


def test_extract_preserves_existing_provenance():
    """Re-extraction keeps the first origin rather than overwriting it."""
    g = _chain()
    g.nodes["a"].properties[SOURCE_GID_KEY] = "original#a"
    sub = extract_subgraph(g, {"a"}, hops=0)
    assert sub.nodes["a"].properties[SOURCE_GID_KEY] == "original#a"


def test_extract_without_source_article_id_skips_stamp():
    """A source graph without an article_id cannot stamp provenance."""
    g = KnowledgeGraph()
    g.add_node(Node(type="claim", id="a"))
    sub = extract_subgraph(g, {"a"}, hops=0)
    assert SOURCE_GID_KEY not in sub.nodes["a"].properties


def test_extract_is_independent_of_source():
    """Mutating the extracted graph does not touch the source."""
    g = _chain()
    sub = extract_subgraph(g, {"a"}, hops=0, article_id="dest")
    sub.nodes["a"].properties["mutated"] = True
    sub.nodes["a"].tags.append("x")
    assert "mutated" not in g.nodes["a"].properties
    assert g.nodes["a"].tags == []
    assert sub.article_id == "dest"


def test_stale_import_clean_and_local_edit():
    """A matching origin is clean; a local edit to the copy is not flagged."""
    g = _chain()
    sub = extract_subgraph(g, {"a"}, hops=0)
    resolve = {"src": g}.get
    assert find_stale_imports(sub, resolve) == []
    sub.nodes["a"].text = "locally annotated"  # editing the copy is fine
    assert find_stale_imports(sub, resolve) == []


def test_stale_import_flags_upstream_change():
    """A change to the origin's text flags the imported copy as changed."""
    g = _chain()
    sub = extract_subgraph(g, {"a"}, hops=0)
    g.nodes["a"].text = "origin corrected"
    stale = find_stale_imports(sub, {"src": g}.get)
    assert [(s.node_id, s.reason) for s in stale] == [("a", "changed")]


def test_stale_import_flags_missing_origin():
    """An unresolvable origin flags the imported copy as missing."""
    g = _chain()
    sub = extract_subgraph(g, {"a"}, hops=0)
    stale = find_stale_imports(sub, lambda _aid: None)
    assert [(s.node_id, s.reason) for s in stale] == [("a", "missing")]


def test_stale_import_ignores_unstamped_nodes():
    """Nodes without a provenance stamp are never reported."""
    g = KnowledgeGraph(article_id="x")
    g.add_node(Node(type="claim", id="c", text="local only"))
    assert find_stale_imports(g, lambda _aid: None) == []
