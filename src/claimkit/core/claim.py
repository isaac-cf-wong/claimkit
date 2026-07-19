"""Backward-compatible aliases for the pre-v-next ``Claim`` model.

``Claim`` is now :class:`~claimkit.core.statement.Statement` (a claim is the
``StatementType.CLAIM`` case) and ``ClaimStatus`` is
:class:`~claimkit.core.statement.StatementStatus`. New code should import from
:mod:`claimkit.core.statement`; these aliases keep existing imports working.
"""

from __future__ import annotations

from claimkit.core.statement import Statement as Claim
from claimkit.core.statement import StatementStatus as ClaimStatus

__all__ = ["Claim", "ClaimStatus"]
