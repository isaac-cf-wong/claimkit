"""Backward-compatible aliases for the pre-v-next ``Claim`` model.

``Claim`` is now :class:`~ideagraph.core.statement.Statement` (a claim is the
``StatementType.CLAIM`` case) and ``ClaimStatus`` is
:class:`~ideagraph.core.statement.StatementStatus`. New code should import from
:mod:`ideagraph.core.statement`; these aliases keep existing imports working.
"""

from __future__ import annotations

from ideagraph.core.statement import Statement as Claim
from ideagraph.core.statement import StatementStatus as ClaimStatus

__all__ = ["Claim", "ClaimStatus"]
