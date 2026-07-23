---
title: Extraction
description: Carve a self-contained subgraph out of a knowledge graph.
---

`extract_subgraph` copies the induced subgraph around a set of seed nodes into a
new, independent graph, stamping each copied node with its origin's global id
and text hash. `find_stale_imports` uses those stamps to report copies whose
origin has since changed or disappeared — only _upstream_ drift is flagged, so
local edits to a copy are ignored. The CLI surfaces this as `stale-import`
warnings under `ideagraph doctor --library <root>`.

<!-- prettier-ignore-start -->

::: ideagraph.kg.extract
    options:
        show_root_heading: false
        heading_level: 2
        inherited_members: true
        show_if_no_docstring: false
        docstring_style: google
        show_source: true

<!-- prettier-ignore-end -->
