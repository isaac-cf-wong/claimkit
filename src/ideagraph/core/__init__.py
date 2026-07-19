"""Core abstractions for ideagraph.

This package holds the primary domain model. The first citizen is the
:class:`~ideagraph.core.claim.Claim`, the central abstraction of the framework.
"""

from __future__ import annotations

from ideagraph.core.activity import Activity, ActivityKind
from ideagraph.core.claim import Claim, ClaimStatus
from ideagraph.core.coverage import ClaimCoverage, claim_coverage, coverage
from ideagraph.core.evidence import Evidence, EvidenceKind, EvidenceRelation
from ideagraph.core.graph import ProvenanceGraph
from ideagraph.core.provenance import NodeType, ProvenancePredicate, ProvenanceRelation
from ideagraph.core.staleness import (
    DigestResolver,
    compute_digest,
    evidence_changed,
    find_stale_claims,
    find_stale_evidence,
    hash_file,
    mark_stale_claims,
)
from ideagraph.core.statement import ASSERTION_TYPES, Statement, StatementStatus, StatementType
from ideagraph.core.validation import (
    ValidationResult,
    apply_all,
    apply_validation,
    validate_all,
    validate_claim,
)

__all__ = [
    "ASSERTION_TYPES",
    "Activity",
    "ActivityKind",
    "Claim",
    "ClaimCoverage",
    "ClaimStatus",
    "DigestResolver",
    "Evidence",
    "EvidenceKind",
    "EvidenceRelation",
    "NodeType",
    "ProvenanceGraph",
    "ProvenancePredicate",
    "ProvenanceRelation",
    "Statement",
    "StatementStatus",
    "StatementType",
    "ValidationResult",
    "apply_all",
    "apply_validation",
    "claim_coverage",
    "compute_digest",
    "coverage",
    "evidence_changed",
    "find_stale_claims",
    "find_stale_evidence",
    "hash_file",
    "mark_stale_claims",
    "validate_all",
    "validate_claim",
]
