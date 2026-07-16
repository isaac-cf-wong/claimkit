---
title: Command line
description: The claimkit command-line interface.
---

ClaimKit ships a `claimkit` command for building and checking a provenance graph
stored as a JSON file. Run `claimkit --help` (or `claimkit COMMAND --help`) for
the authoritative, always-current option list.

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
claimkit init graph.json
CLAIM=$(claimkit add-claim graph.json "Half-life measured at 5.2 days." --tag decay)
claimkit add-evidence graph.json "$CLAIM" \
    --kind workflow --reference run-42 --digest sha256:abc123

claimkit validate graph.json --apply
claimkit report graph.json
```
