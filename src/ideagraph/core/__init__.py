"""Model-agnostic graph utilities.

The typed provenance model that once lived here (Statement / Evidence / Activity
/ ProvenanceGraph and their semantics) has been replaced by the generic
knowledge-graph core in :mod:`ideagraph.kg`. What remains are the two
domain-neutral helpers the rest of the package still builds on: global-id
identity and content digests.
"""

from __future__ import annotations

from ideagraph.core.identity import SEP, global_id, is_global_id, parse_global_id
from ideagraph.core.staleness import compute_digest, hash_file

__all__ = [
    "SEP",
    "compute_digest",
    "global_id",
    "hash_file",
    "is_global_id",
    "parse_global_id",
]
