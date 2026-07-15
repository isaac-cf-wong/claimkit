"""Core abstractions for claimkit.

This package holds the primary domain model. The first citizen is the
:class:`~claimkit.core.claim.Claim`, the central abstraction of the framework.
"""

from __future__ import annotations

from claimkit.core.claim import Claim, ClaimStatus
from claimkit.core.evidence import Evidence, EvidenceKind, EvidenceRelation

__all__ = ["Claim", "ClaimStatus", "Evidence", "EvidenceKind", "EvidenceRelation"]
