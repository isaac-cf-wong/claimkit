---
title: Command line
description: The ideagraph command-line interface.
---

ideagraph ships a `ideagraph` command for building and checking a provenance
graph stored as a JSON file. Run `ideagraph --help` (or
`ideagraph COMMAND --help`) for the authoritative, always-current option list.

## Commands

- **`init GRAPH.json`** – create an empty graph file. Refuses to overwrite an
  existing file unless `--force`.
- **`add-claim GRAPH.json STATEMENT`** – append a claim and print its id.
  Options: `--id`, `--tag` (repeatable).
- **`add-evidence GRAPH.json CLAIM_ID`** – append evidence and link it to a
  claim. Options: `--kind`, `--reference`, `--relation`
  (`supports`/`refutes`/`contextual`), `--id`, `--digest`, `--description`.
- **`validate GRAPH.json`** – resolve each claim's status from its evidence.
  Options: `--apply` (persist), `--json`.
- **`mark GRAPH.json CLAIM_ID STATUS`** – set a claim's status manually
  (human-assisted review). Option: `--note`.
- **`stale GRAPH.json`** – flag claims whose supporting artefacts have changed
  on disk. Options: `--base`, `--apply`, `--json`.
- **`report GRAPH.json`** – render a Markdown provenance report. Option:
  `-o/--output`.
- **`export GRAPH.json`** – export the graph to W3C PROV-JSON. Option:
  `-o/--output`.
- **`import SOURCE.json DEST.json`** – import a PROV-JSON document into a graph
  file. Option: `--force`.

## Example

```bash
ideagraph init graph.json
CLAIM=$(ideagraph add-claim graph.json "Half-life measured at 5.2 days." --tag decay)
ideagraph add-evidence graph.json "$CLAIM" \
    --kind workflow --reference run-42 --digest sha256:abc123

ideagraph validate graph.json --apply
ideagraph report graph.json
```
