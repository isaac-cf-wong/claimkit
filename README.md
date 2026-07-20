# ideagraph

[![Python CI](https://github.com/isaac-cf-wong/claimkit/actions/workflows/ci.yml/badge.svg)](https://github.com/isaac-cf-wong/claimkit/actions/workflows/ci.yml)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/isaac-cf-wong/claimkit/main.svg)](https://results.pre-commit.ci/latest/github/isaac-cf-wong/claimkit/main)
[![Documentation Status](https://github.com/isaac-cf-wong/claimkit/actions/workflows/documentation.yml/badge.svg)](https://isaac-cf-wong.github.io/claimkit/)
[![codecov](https://codecov.io/gh/isaac-cf-wong/claimkit/graph/badge.svg?token=COF8341N60)](https://codecov.io/gh/isaac-cf-wong/claimkit)
[![PyPI Version](https://img.shields.io/pypi/v/ideagraph)](https://pypi.org/project/ideagraph/)
[![Python Versions](https://img.shields.io/pypi/pyversions/ideagraph)](https://pypi.org/project/ideagraph/)
[![License](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![DOI](https://zenodo.org/badge/1301566989.svg)](https://doi.org/10.5281/zenodo.21396634)
[![SPEC 0 — Minimum Supported Dependencies](https://img.shields.io/badge/SPEC-0-green?labelColor=%23004811&color=%235CA038)](https://scientific-python.org/specs/spec-0000/)

**ideagraph is an idea-graph engine for scientific writing and reading.**

It turns an article into a reusable asset: a graph whose nodes are the article's
statements (its ideas) and whose edges are the relationships between them —
elaboration, contrast, dependence, citation. The graph is structured data that
lets humans and AI agents navigate the relationships of ideas quickly, track a
draft's structure and gaps, and connect ideas across articles.

Building the graph is a judgement call — deciding what counts as a statement,
and how statements relate, is left to a human or an LLM driving the same CLI.
ideagraph provides the framework, storage, and navigation, not automatic
extraction. Every interface is machine-readable so humans and agents share one
tool.

**Provenance** is one built-in layer: a statement can carry evidence, be
validated against it, and be flagged _stale_ when that evidence changes — but it
is a facet of a statement node, not the whole story.

> ideagraph was previously released as **ClaimKit**. The `claimkit` import and
> CLI still work as a deprecated alias and will be removed in a future release.

## Core concepts

- **Statement** — a unit of meaning in an article: a typed node (claim, finding,
  background, method, definition, motivation, result, …) with a stable id, text,
  and metadata. `claim` is one statement type, not the whole model.
- **Relation** — a typed, directed edge between statements: discourse links
  (elaborates, contrasts, depends_on, cites, motivates) and provenance links.
- **Evidence** — a link from a statement to an artefact (code, data, a run,
  literature, …) that supports, refutes, or contextualises it.
- **Activity** — a process (computation, measurement, analysis, review) that
  consumed and produced artefacts.
- **ProvenanceGraph** — the container of nodes and edges; supports traversal,
  coverage, validation, staleness detection, and reporting.

An asserting statement's provenance status is one of `unresolved`, `valid`,
`invalid`, `stale`, or `needs_review`.

## Installation

```bash
pip install ideagraph
```

Requires Python 3.12+.

## Command-line quickstart

Build a graph, link evidence, and check it — all from the terminal:

```bash
ideagraph init graph.json
CLAIM=$(ideagraph add-claim graph.json "Half-life measured at 5.2 days." --tag decay)
ideagraph add-evidence graph.json "$CLAIM" \
    --kind workflow --reference run-42 --digest sha256:abc123

ideagraph validate graph.json            # resolve status from evidence
ideagraph stale graph.json               # flag claims whose artefacts changed
ideagraph report graph.json              # human-readable Markdown report
ideagraph export graph.json -o prov.json # export to W3C PROV-JSON
ideagraph import prov.json restored.json # import PROV-JSON back into a graph
```

`validate` and `stale` accept `--json` for machine-readable output; `report` and
`export` accept `-o` to write to a file. Run `ideagraph --help` for the full
command list.

## Python quickstart

```python
from ideagraph import (
    Claim, Evidence, EvidenceKind, NodeType,
    ProvenanceGraph, ProvenancePredicate, ProvenanceRelation,
    validate_claim, render_report,
)

graph = ProvenanceGraph()
graph.add_claim(Claim(statement="Half-life measured at 5.2 days.", id="c1"))
graph.add_evidence(
    Evidence(claim_id="c1", kind=EvidenceKind.WORKFLOW, reference="run-42", id="e1")
)
graph.add_relation(
    ProvenanceRelation(
        subject_type=NodeType.CLAIM, subject_id="c1",
        predicate=ProvenancePredicate.SUPPORTED_BY,
        object_type=NodeType.EVIDENCE, object_id="e1",
    )
)

result = validate_claim(graph, "c1")
print(result.status, "—", result.reason)   # valid — supported by 1 piece(s) of evidence
print(render_report(graph))
```

## Interoperability

ideagraph graphs serialise to a versioned JSON format for storage (`save_graph`
/ `load_graph`) and export to / import from
[W3C PROV-JSON](https://www.w3.org/submissions/prov-json/) (`to_prov` /
`from_prov`) for interchange with the wider provenance ecosystem.

## License

BSD 3-Clause. See [LICENSE](LICENSE).
