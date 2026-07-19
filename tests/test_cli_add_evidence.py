"""Tests for the ``claimkit add-evidence`` command."""

from __future__ import annotations

from typer.testing import CliRunner

from claimkit.cli.main import app
from claimkit.core import ProvenancePredicate
from claimkit.persistence import load_graph

runner = CliRunner()


def _graph_with_claim(path):
    """Create a graph file holding one claim ``c1``.

    Args:
        path: Destination graph file path.

    Returns:
        The path written to.

    """
    runner.invoke(app, ["init", str(path)])
    runner.invoke(app, ["add-claim", str(path), "A", "--id", "c1"])
    return path


def test_add_evidence_links_and_prints_id(tmp_path):
    """add-evidence stores evidence, links it, and prints its id.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    path = _graph_with_claim(tmp_path / "g.json")
    result = runner.invoke(
        app,
        ["add-evidence", str(path), "c1", "--kind", "data", "--reference", "dataset.csv"],
    )
    assert result.exit_code == 0
    ev_id = result.stdout.strip()
    graph = load_graph(path)
    ev = graph.evidence[ev_id]
    assert ev.kind.value == "data"
    assert ev.reference == "dataset.csv"
    assert ev.relation.value == "supports"
    edges = graph.outgoing("c1")
    assert len(edges) == 1
    assert edges[0].predicate is ProvenancePredicate.SUPPORTED_BY
    assert edges[0].object_id == ev_id


def test_add_evidence_refutes_uses_refuted_by(tmp_path):
    """A refuting relation records a REFUTED_BY edge.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    path = _graph_with_claim(tmp_path / "g.json")
    runner.invoke(
        app,
        ["add-evidence", str(path), "c1", "--kind", "data", "--reference", "r", "--relation", "refutes"],
    )
    edge = load_graph(path).outgoing("c1")[0]
    assert edge.predicate is ProvenancePredicate.REFUTED_BY


def test_add_evidence_contextual_uses_relates_to(tmp_path):
    """A contextual relation records a RELATES_TO edge.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    path = _graph_with_claim(tmp_path / "g.json")
    runner.invoke(
        app,
        ["add-evidence", str(path), "c1", "--kind", "data", "--reference", "r", "--relation", "contextual"],
    )
    edge = load_graph(path).outgoing("c1")[0]
    assert edge.predicate is ProvenancePredicate.RELATES_TO


def test_add_evidence_honours_id_digest_description(tmp_path):
    """Explicit id, digest, and description are stored.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    path = _graph_with_claim(tmp_path / "g.json")
    result = runner.invoke(
        app,
        [
            "add-evidence",
            str(path),
            "c1",
            "--kind",
            "workflow",
            "--reference",
            "run-42",
            "--id",
            "e1",
            "--digest",
            "sha256:aa",
            "--description",
            "the run",
        ],
    )
    assert result.stdout.strip() == "e1"
    ev = load_graph(path).evidence["e1"]
    assert ev.digest == "sha256:aa"
    assert ev.description == "the run"


def test_add_evidence_unknown_claim(tmp_path):
    """Linking to a missing claim exits non-zero.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    path = _graph_with_claim(tmp_path / "g.json")
    result = runner.invoke(
        app,
        ["add-evidence", str(path), "missing", "--kind", "data", "--reference", "r"],
    )
    assert result.exit_code == 1
    assert "No such statement" in result.stderr


def test_add_evidence_duplicate_id(tmp_path):
    """Reusing an evidence id exits non-zero.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    path = _graph_with_claim(tmp_path / "g.json")
    args = ["add-evidence", str(path), "c1", "--kind", "data", "--reference", "r", "--id", "e1"]
    runner.invoke(app, args)
    result = runner.invoke(app, args)
    assert result.exit_code == 1
    assert "already exists" in result.stderr


def test_add_evidence_missing_file(tmp_path):
    """add-evidence on a missing file exits non-zero.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    result = runner.invoke(
        app,
        ["add-evidence", str(tmp_path / "nope.json"), "c1", "--kind", "data", "--reference", "r"],
    )
    assert result.exit_code == 1
    assert "No such file" in result.stderr


def test_add_evidence_then_validate_is_valid(tmp_path):
    """A claim gains VALID status once supporting evidence is added.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    path = _graph_with_claim(tmp_path / "g.json")
    runner.invoke(app, ["add-evidence", str(path), "c1", "--kind", "data", "--reference", "r"])
    result = runner.invoke(app, ["validate", str(path)])
    assert "c1: valid" in result.stdout
