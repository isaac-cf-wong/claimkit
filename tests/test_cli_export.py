"""Tests for the ``claimkit export`` CLI command."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from claimkit.cli.main import app
from claimkit.core import (
    Claim,
    Evidence,
    EvidenceKind,
    NodeType,
    ProvenanceGraph,
    ProvenancePredicate,
    ProvenanceRelation,
)
from claimkit.persistence import save_graph
from claimkit.prov import CK_NAMESPACE

runner = CliRunner()


def _graph_file(path):
    """Write a graph with one claim supported by one piece of evidence.

    Args:
        path: Destination graph file path.

    Returns:
        The path written to.

    """
    g = ProvenanceGraph()
    g.add_claim(Claim(statement="A", id="c1"))
    g.add_evidence(Evidence(claim_id="c1", kind=EvidenceKind.DATA, reference="r", id="e1"))
    g.add_relation(
        ProvenanceRelation(
            subject_type=NodeType.CLAIM,
            subject_id="c1",
            predicate=ProvenancePredicate.SUPPORTED_BY,
            object_type=NodeType.EVIDENCE,
            object_id="e1",
            id="s1",
        )
    )
    save_graph(g, path)
    return path


def test_export_stdout_is_prov_json(tmp_path):
    """Export prints PROV-JSON to stdout.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    path = _graph_file(tmp_path / "g.json")
    result = runner.invoke(app, ["export", str(path)])
    assert result.exit_code == 0
    doc = json.loads(result.stdout)
    assert doc["prefix"]["ck"] == CK_NAMESPACE
    assert doc["entity"]["ck:c1"]["prov:type"] == "ck:Claim"
    assert "ck:s1" in doc["wasInfluencedBy"]


def test_export_to_file(tmp_path):
    """Export -o writes PROV-JSON to a file with a trailing newline.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    path = _graph_file(tmp_path / "g.json")
    out = tmp_path / "out" / "prov.json"
    result = runner.invoke(app, ["export", str(path), "-o", str(out)])
    assert result.exit_code == 0
    text = out.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert json.loads(text)["entity"]["ck:c1"]["prov:type"] == "ck:Claim"


def test_export_missing_file(tmp_path):
    """A missing input file exits non-zero with a message.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    result = runner.invoke(app, ["export", str(tmp_path / "nope.json")])
    assert result.exit_code == 1
    assert "No such file" in result.stderr
