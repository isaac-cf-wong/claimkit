"""Tests for ``--created-at`` backdating on the add-* commands."""

from __future__ import annotations

from datetime import datetime

from typer.testing import CliRunner

from claimkit.cli.main import app
from claimkit.persistence import load_graph

runner = CliRunner()

WHEN = "2026-06-13T12:51:00"


def _graph(path):
    """Create an empty graph file with one claim ``c1``.

    Args:
        path: Destination graph file path.

    Returns:
        The path written to.

    """
    runner.invoke(app, ["init", str(path)])
    runner.invoke(app, ["add-claim", str(path), "A", "--id", "c1", "--created-at", WHEN])
    return path


def test_add_claim_created_at(tmp_path):
    """add-claim backdates the claim's created_at.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    path = _graph(tmp_path / "g.json")
    assert load_graph(path).claims["c1"].created_at == datetime.fromisoformat(WHEN)


def test_add_evidence_and_activity_created_at(tmp_path):
    """add-evidence and add-activity backdate created_at too.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    path = _graph(tmp_path / "g.json")
    runner.invoke(
        app,
        ["add-evidence", str(path), "c1", "--kind", "data", "--reference", "r", "--id", "e1", "--created-at", WHEN],
    )
    runner.invoke(
        app,
        ["add-activity", str(path), "run", "--kind", "computation", "--id", "a1", "--created-at", WHEN],
    )
    g = load_graph(path)
    assert g.evidence["e1"].created_at == datetime.fromisoformat(WHEN)
    assert g.activities["a1"].created_at == datetime.fromisoformat(WHEN)


def test_bad_created_at(tmp_path):
    """A non-ISO --created-at exits non-zero.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    path = tmp_path / "g.json"
    runner.invoke(app, ["init", str(path)])
    result = runner.invoke(app, ["add-claim", str(path), "A", "--created-at", "june"])
    assert result.exit_code != 0
