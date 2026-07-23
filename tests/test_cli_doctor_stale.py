"""Tests for ``ideagraph doctor --library`` import-staleness detection."""

from __future__ import annotations

from typer.testing import CliRunner

from ideagraph.cli.main import app
from ideagraph.kg import KnowledgeGraph, Node, extract_subgraph
from ideagraph.kg.persistence import load_graph, save_graph

runner = CliRunner()


def _cache_and_project(tmp_path):
    """Build a one-article cache and a project graph importing from it.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        A (cache_dir, article_path, project_path) tuple.

    """
    cache = tmp_path / "cache"
    cache.mkdir()
    art = KnowledgeGraph(article_id="cache_art")
    art.add_node(Node(type="finding", id="f", text="original text", properties={"status": "valid"}))
    art_path = cache / "cache_art.json"
    save_graph(art, art_path)

    project = extract_subgraph(art, {"f"}, hops=0, article_id="proj")
    project_path = tmp_path / "proj.json"
    save_graph(project, project_path)
    return cache, art_path, project_path


def test_doctor_reports_no_staleness_when_unchanged(tmp_path):
    """A fresh import is not flagged.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    cache, _art, project = _cache_and_project(tmp_path)
    result = runner.invoke(app, ["doctor", str(project), "--library", str(cache)])
    assert result.exit_code == 0
    assert "stale-import" not in result.stdout


def test_doctor_flags_stale_import_after_origin_change(tmp_path):
    """Editing the cache origin flags the imported copy as stale.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    cache, art_path, project = _cache_and_project(tmp_path)
    art = load_graph(art_path)
    art.nodes["f"].text = "origin corrected text"
    save_graph(art, art_path)

    result = runner.invoke(app, ["doctor", str(project), "--library", str(cache)])
    # a stale import is a warning, not an error: still exit 0 without --strict
    assert result.exit_code == 0
    assert "stale-import" in result.stdout
    assert "cache_art#f" in result.stdout


def test_doctor_strict_fails_on_stale_import(tmp_path):
    """With --strict a stale import (warning) fails the run.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    cache, art_path, project = _cache_and_project(tmp_path)
    art = load_graph(art_path)
    art.nodes["f"].text = "changed"
    save_graph(art, art_path)

    result = runner.invoke(app, ["doctor", str(project), "--library", str(cache), "--strict"])
    assert result.exit_code == 1
