"""Tests for support-coverage classification and the ``coverage`` command."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from ideagraph import (
    Claim,
    Evidence,
    EvidenceKind,
    NodeType,
    ProvenanceGraph,
    ProvenancePredicate,
    ProvenanceRelation,
    coverage,
)
from ideagraph.cli.main import app
from ideagraph.persistence import save_graph

runner = CliRunner()


def _link(graph, claim_id, ev):
    """Add evidence and a SUPPORTED_BY edge from the claim to it."""
    graph.add_evidence(ev)
    graph.add_relation(
        ProvenanceRelation(
            subject_type=NodeType.CLAIM,
            subject_id=claim_id,
            predicate=ProvenancePredicate.SUPPORTED_BY,
            object_type=NodeType.EVIDENCE,
            object_id=ev.id,
        )
    )


def _graph():
    """Build a graph with own / literature / both / unsupported claims."""
    g = ProvenanceGraph()
    for cid in ("c_own", "c_lit", "c_both", "c_none"):
        g.add_claim(Claim(statement=cid, id=cid))
    _link(g, "c_own", Evidence(claim_id="c_own", kind=EvidenceKind.DATA, reference="run-1"))
    _link(g, "c_lit", Evidence(claim_id="c_lit", kind=EvidenceKind.LITERATURE, reference="Chan2020"))
    _link(g, "c_both", Evidence(claim_id="c_both", kind=EvidenceKind.FIGURE, reference="fig.png"))
    _link(g, "c_both", Evidence(claim_id="c_both", kind=EvidenceKind.LITERATURE, reference="10.0/x"))
    return g


def test_coverage_categories():
    """Coverage classifies each claim by support origin."""
    cov = coverage(_graph())
    assert cov["c_own"].category == "own"
    assert cov["c_lit"].category == "literature"
    assert cov["c_both"].category == "both"
    assert cov["c_none"].category == "unsupported"
    assert cov["c_none"].supported is False
    assert cov["c_lit"].has_literature is True
    assert set(cov["c_both"].evidence_kinds) == {"figure", "literature"}


def test_coverage_ignores_non_supported_edges():
    """RELATES_TO / REFUTED_BY evidence does not count as support."""
    g = ProvenanceGraph()
    g.add_claim(Claim(statement="c", id="c"))
    ev = Evidence(claim_id="c", kind=EvidenceKind.DATA, reference="r")
    g.add_evidence(ev)
    g.add_relation(
        ProvenanceRelation(
            subject_type=NodeType.CLAIM,
            subject_id="c",
            predicate=ProvenancePredicate.RELATES_TO,
            object_type=NodeType.EVIDENCE,
            object_id=ev.id,
        )
    )
    assert coverage(g)["c"].category == "unsupported"


def test_coverage_cli_text_and_json(tmp_path):
    """The coverage command prints categories and valid JSON.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    path = tmp_path / "g.json"
    save_graph(_graph(), path)

    text = runner.invoke(app, ["coverage", str(path)])
    assert text.exit_code == 0
    assert "c_none: unsupported" in text.stdout
    assert "c_both: both" in text.stdout

    js = runner.invoke(app, ["coverage", str(path), "--json"])
    data = json.loads(js.stdout)
    assert data["c_lit"]["category"] == "literature"


def test_coverage_cli_strict_exits_nonzero(tmp_path):
    """--strict exits non-zero when a claim is unsupported.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    path = tmp_path / "g.json"
    save_graph(_graph(), path)
    result = runner.invoke(app, ["coverage", str(path), "--strict"])
    assert result.exit_code == 1
    assert "unsupported claim" in result.stderr
