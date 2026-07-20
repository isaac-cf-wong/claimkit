"""CLI tests for Phase D discovery: find / neighbors / backlinks / path / gaps."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from ideagraph import Library, ProvenancePredicate
from ideagraph.cli.main import app

runner = CliRunner()


def _statement(path, node_id, text, *, stype="claim", status="unresolved"):
    """Add a statement to a graph file via the CLI.

    Args:
        path: Graph file path.
        node_id: Statement id.
        text: Statement text.
        stype: Rhetorical type.
        status: Initial status.

    """
    runner.invoke(app, ["add-statement", str(path), text, "--id", node_id, "--type", stype, "--status", status])


def _library(tmp_path):
    """Build a two-article library with intra + cross edges and return its root.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    a = tmp_path / "A.json"
    b = tmp_path / "B.json"
    runner.invoke(app, ["init", str(a), "--article-id", "paperA"])
    runner.invoke(app, ["init", str(b), "--article-id", "paperB"])
    _statement(a, "c1", "Time-slides fail in the signal-dominated regime.", stype="finding")
    _statement(a, "c2", "Reported FARs are untrustworthy.", stype="claim")
    _statement(b, "f1", "Glitches inflate the false-alarm rate.", stype="finding", status="valid")
    runner.invoke(app, ["add-relation", str(a), "c2", "c1", "--predicate", "depends_on"])
    runner.invoke(app, ["add-xref", str(a), "c1", "builds_on", "paperB#f1"])
    return tmp_path


def test_find(tmp_path):
    """Find returns matching statements, filterable by type.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    root = _library(tmp_path)
    out = runner.invoke(app, ["find", str(root), "false-alarm", "--json"])
    assert out.exit_code == 0
    hits = json.loads(out.stdout)
    assert any(h["gid"] == "paperB#f1" for h in hits)

    typed = runner.invoke(app, ["find", str(root), "regime", "--type", "claim", "--json"])
    assert json.loads(typed.stdout) == []  # the match is a finding, not a claim


def test_neighbors_both_directions(tmp_path):
    """Neighbors lists intra and cross edges around a statement.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    root = _library(tmp_path)
    out = runner.invoke(app, ["neighbors", str(root), "paperA#c1", "--json"])
    edges = json.loads(out.stdout)
    kinds = {(e["predicate"], e["kind"]) for e in edges}
    assert ("depends_on", "intra") in kinds  # incoming from c2
    assert ("builds_on", "cross") in kinds  # outgoing to paperB#f1


def test_backlinks(tmp_path):
    """Backlinks shows cross-article references pointing at a statement.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    root = _library(tmp_path)
    out = runner.invoke(app, ["backlinks", str(root), "paperB#f1", "--json"])
    edges = json.loads(out.stdout)
    assert any(e["src"] == "paperA#c1" and e["kind"] == "cross" for e in edges)


def test_path_found_and_absent(tmp_path):
    """Path traces edges across articles and fails cleanly when none exists.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    root = _library(tmp_path)
    found = runner.invoke(app, ["path", str(root), "paperA#c2", "paperB#f1", "--json"])
    payload = json.loads(found.stdout)
    assert payload["found"] is True
    assert [s["gid"] for s in payload["path"]] == ["paperA#c2", "paperA#c1", "paperB#f1"]

    absent = runner.invoke(app, ["path", str(root), "paperB#f1", "paperA#c2"])
    assert absent.exit_code == 1  # edges are directed; no reverse path


def test_gaps(tmp_path):
    """Gaps lists unsupported assertions and dangling cross-references.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    root = _library(tmp_path)
    # Add a dangling cross-reference from A to a missing node in B.
    runner.invoke(app, ["add-xref", str(root / "A.json"), "c2", "cites", "paperB#ghost"])
    out = runner.invoke(app, ["gaps", str(root), "--json"])
    payload = json.loads(out.stdout)
    unsupported = {h["gid"] for h in payload["unsupported_assertions"]}
    assert "paperA#c1" in unsupported  # unresolved finding
    assert "paperA#c2" in unsupported  # unresolved claim
    assert "paperB#f1" not in unsupported  # status valid
    assert any(e["target"] == "paperB#ghost" for e in payload["dangling_cross_references"])

    strict = runner.invoke(app, ["gaps", str(root), "--strict"])
    assert strict.exit_code == 1


def test_library_path_direct_api(tmp_path):
    """Library.path returns the same-node trivial path and respects depth.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    root = _library(tmp_path)
    with Library(root) as lib:
        lib.index()
        assert lib.path("paperA#c1", "paperA#c1") == ["paperA#c1"]
        assert lib.path("paperA#c2", "paperB#f1", max_depth=1) is None  # needs 2 hops
        _ = ProvenancePredicate.CITES  # predicate enum importable alongside
