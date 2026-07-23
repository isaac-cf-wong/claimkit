# ideagraph

[![Python CI](https://github.com/isaac-cf-wong/ideagraph/actions/workflows/ci.yml/badge.svg)](https://github.com/isaac-cf-wong/ideagraph/actions/workflows/ci.yml)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/isaac-cf-wong/ideagraph/main.svg)](https://results.pre-commit.ci/latest/github/isaac-cf-wong/ideagraph/main)
[![Documentation Status](https://github.com/isaac-cf-wong/ideagraph/actions/workflows/documentation.yml/badge.svg)](https://isaac-cf-wong.github.io/ideagraph/)
[![codecov](https://codecov.io/gh/isaac-cf-wong/ideagraph/graph/badge.svg?token=COF8341N60)](https://codecov.io/gh/isaac-cf-wong/ideagraph)
[![PyPI Version](https://img.shields.io/pypi/v/ideagraph)](https://pypi.org/project/ideagraph/)
[![Python Versions](https://img.shields.io/pypi/pyversions/ideagraph)](https://pypi.org/project/ideagraph/)
[![License](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![DOI](https://zenodo.org/badge/1301566989.svg)](https://doi.org/10.5281/zenodo.21396634)
[![SPEC 0 — Minimum Supported Dependencies](https://img.shields.io/badge/SPEC-0-green?labelColor=%23004811&color=%235CA038)](https://scientific-python.org/specs/spec-0000/)

**ideagraph is an engine for representing knowledge as a graph.**

Each node carries one piece of information; edges are the typed relationships
between pieces. A **profile** gives a graph its vocabulary and rules, so the
same engine can model any domain. The built-in **research** profile reproduces
ideagraph's original purpose — turning an article into a graph of its statements
(claims, findings, methods, …), the discourse links between them, and the
evidence that supports them — with support coverage, validation, and staleness
as facets of that profile.

Every interface is machine-readable, so humans and AI agents share one tool. AI
agents build and edit graphs through the CLI (which validates writes and returns
actionable errors); humans read, visualise, and share graphs through the Django
web interface.

> ideagraph was previously released as **ClaimKit**. The `claimkit` package has
> been renamed — install `ideagraph`.

## Core concepts

- **Node** — one piece of information: a typed node (its `type` drawn from the
  active profile's vocabulary) with a stable id, text, tags, and free-form
  `properties`.
- **Edge** — a typed, directed connection between two nodes. A cross-article
  edge simply targets a global `article#node` id in another graph.
- **KnowledgeGraph** — the container of nodes and edges; supports traversal and
  a flat, versioned JSON serialisation.
- **Profile** — the schema that gives a graph meaning: the node and edge types
  it may use, endpoint constraints, and required properties. The **research**
  profile defines statement types (claim, finding, background, method, …),
  `evidence` and `activity` nodes, and the provenance / discourse /
  cross-article edge types, plus coverage, validation, and staleness.

Under the research profile, an asserting statement's status is one of
`unresolved`, `valid`, `invalid`, `stale`, or `needs_review`.

## Installation

```bash
pip install ideagraph
```

Requires Python 3.12+. The web interface + REST API are an optional extra:
`pip install ideagraph[web]`.

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
from ideagraph import Edge, KnowledgeGraph, Node, render_report, validate_all

graph = KnowledgeGraph()
graph.add_node(Node(type="claim", id="c1", text="Half-life measured at 5.2 days."))
graph.add_node(
    Node(type="evidence", id="e1", properties={"kind": "workflow", "reference": "run-42"})
)
graph.add_edge(Edge(type="supported_by", source="c1", target="e1"))

result = validate_all(graph)["c1"]
print(result.status, "—", result.reason)   # valid — supported by 1 piece(s)
print(render_report(graph))
```

Validate a graph against its profile's rules:

```python
from ideagraph import get_profile

diagnostics = get_profile("research").validate(graph)  # [] when the graph conforms
```

## Web interface

`pip install ideagraph[web]` adds a Django server: a hostable web UI to
visualise graphs and a token-authenticated REST API to share them with
collaborators (per-graph owner/collaborator permissions). Run it with
`python manage.py migrate && python manage.py runserver`; the local CLI can push
and pull graphs to a hosted server with `ideagraph remote`.

## Interoperability

ideagraph graphs serialise to a versioned JSON format for storage (`save_graph`
/ `load_graph`) and export to / import from
[W3C PROV-JSON](https://www.w3.org/submissions/prov-json/) (`to_prov` /
`from_prov`) for interchange with the wider provenance ecosystem.

## License

BSD 3-Clause. See [LICENSE](LICENSE).
