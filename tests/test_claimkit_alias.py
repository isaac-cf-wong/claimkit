"""The deprecated ``claimkit`` name aliases the renamed ``ideagraph`` package."""

from __future__ import annotations

import warnings


def test_top_level_alias_redirects_and_warns():
    """``import claimkit`` redirects to ideagraph and emits a DeprecationWarning."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        import claimkit

        assert any(issubclass(w.category, DeprecationWarning) for w in caught)

    # Public API mirrored onto the alias package.
    assert claimkit.Statement.__module__.startswith("ideagraph")
    stmt = claimkit.Statement(statement="x", id="c1")
    assert stmt.id == "c1"


def test_submodule_imports_redirect():
    """``from claimkit.x import y`` resolves to the matching ideagraph module."""
    from claimkit.core.statement import Statement as AliasStatement
    from claimkit.persistence import save_graph as alias_save

    from ideagraph.core.statement import Statement as RealStatement
    from ideagraph.persistence import save_graph as real_save

    assert AliasStatement is RealStatement
    assert alias_save is real_save


def test_alias_graph_roundtrips_with_real_package(tmp_path):
    """A graph built via the alias is identical to one built via ideagraph.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    import claimkit
    from ideagraph.persistence import load_graph

    g = claimkit.ProvenanceGraph()
    g.add_statement(claimkit.Statement(statement="aliased", id="c1"))
    path = tmp_path / "g.json"
    claimkit.save_graph(g, path)

    reloaded = load_graph(path)  # loaded via the real package
    assert reloaded.statements["c1"].statement == "aliased"
