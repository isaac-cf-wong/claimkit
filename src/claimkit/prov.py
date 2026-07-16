"""Exporting a provenance graph to `PROV-JSON <https://www.w3.org/submissions/prov-json/>`_.

PROV-JSON is a standard JSON serialisation of the `W3C PROV data model
<https://www.w3.org/TR/prov-dm/>`_. Exporting to it lets claimkit provenance be
consumed by the wider provenance ecosystem (validators, visualisers, stores).

The mapping is:

* :class:`~claimkit.core.claim.Claim` and
  :class:`~claimkit.core.evidence.Evidence` nodes -> ``prov:Entity``
* :class:`~claimkit.core.activity.Activity` nodes -> ``prov:Activity``
* edge endpoints typed :attr:`~claimkit.core.provenance.NodeType.ARTEFACT`
  -> ``prov:Entity`` stubs, and :attr:`~claimkit.core.provenance.NodeType.AGENT`
  -> ``prov:Agent`` stubs (they have no dedicated node model yet)
* edges map to the PROV relation that matches their predicate; the claimkit-only
  predicates (``SUPPORTED_BY``, ``REFUTED_BY``, ``REVIEWED_BY``, ``RELATES_TO``)
  have no PROV equivalent and are exported as ``wasInfluencedBy`` carrying a
  ``ck:predicate`` attribute so the original relationship is not lost.

All identifiers are emitted as qualified names in the ``ck`` namespace.
"""

from __future__ import annotations

import json
from typing import Any

from claimkit.core.graph import ProvenanceGraph
from claimkit.core.provenance import NodeType, ProvenancePredicate

#: Namespace prefix mapping emitted in the PROV-JSON document.
CK_NAMESPACE = "https://claimkit.dev/ns#"


def _qn(identifier: str) -> str:
    """Return the ``ck``-prefixed qualified name for an identifier.

    Args:
        identifier: A claimkit node or edge id.

    Returns:
        The qualified name, e.g. ``"ck:c1"``.

    """
    return f"ck:{identifier}"


def _relation_entry(subject: str, predicate: ProvenancePredicate, obj: str) -> tuple[str, dict[str, Any]]:
    """Map an edge to its PROV relation name and payload.

    Predicates with no PROV equivalent fall through to ``wasInfluencedBy``,
    which carries a ``ck:predicate`` attribute preserving the original relation.

    Args:
        subject: The ``ck``-qualified subject id.
        predicate: The edge predicate.
        obj: The ``ck``-qualified object id.

    Returns:
        A ``(relation_name, payload)`` pair for the PROV-JSON document.

    """
    if predicate is ProvenancePredicate.USED:
        return "used", {"prov:activity": subject, "prov:entity": obj}
    if predicate is ProvenancePredicate.GENERATED_BY:
        return "wasGeneratedBy", {"prov:entity": subject, "prov:activity": obj}
    if predicate is ProvenancePredicate.DERIVED_FROM:
        return "wasDerivedFrom", {"prov:generatedEntity": subject, "prov:usedEntity": obj}
    if predicate is ProvenancePredicate.ATTRIBUTED_TO:
        return "wasAttributedTo", {"prov:entity": subject, "prov:agent": obj}
    return "wasInfluencedBy", {
        "prov:influencee": subject,
        "prov:influencer": obj,
        "ck:predicate": predicate.value,
    }


def to_prov(graph: ProvenanceGraph) -> dict[str, Any]:
    """Convert a provenance graph to a PROV-JSON document.

    Args:
        graph: The graph to export.

    Returns:
        A PROV-JSON document as a plain dictionary.

    """
    entity: dict[str, Any] = {}
    activity: dict[str, Any] = {}
    agent: dict[str, Any] = {}

    for claim in graph.claims.values():
        entity[_qn(claim.id)] = {
            "prov:type": "ck:Claim",
            "ck:statement": claim.statement,
            "ck:status": claim.status.value,
        }
    for ev in graph.evidence.values():
        attrs = {
            "prov:type": "ck:Evidence",
            "ck:kind": ev.kind.value,
            "ck:reference": ev.reference,
        }
        if ev.digest is not None:
            attrs["ck:digest"] = ev.digest
        entity[_qn(ev.id)] = attrs
    for act in graph.activities.values():
        attrs = {"prov:type": "ck:Activity", "prov:label": act.label}
        if act.started_at is not None:
            attrs["prov:startTime"] = act.started_at.isoformat()
        if act.ended_at is not None:
            attrs["prov:endTime"] = act.ended_at.isoformat()
        activity[_qn(act.id)] = attrs

    # Collections keyed by NodeType so edge endpoints land in the right bucket.
    buckets = {
        NodeType.CLAIM: (entity, "ck:Claim"),
        NodeType.EVIDENCE: (entity, "ck:Evidence"),
        NodeType.ARTEFACT: (entity, "ck:Artefact"),
        NodeType.ACTIVITY: (activity, "ck:Activity"),
        NodeType.AGENT: (agent, "ck:Agent"),
    }

    def _ensure(node_type: NodeType, node_id: str) -> None:
        collection, prov_type = buckets[node_type]
        collection.setdefault(_qn(node_id), {"prov:type": prov_type})

    relations: dict[str, dict[str, Any]] = {
        "used": {},
        "wasGeneratedBy": {},
        "wasDerivedFrom": {},
        "wasAttributedTo": {},
        "wasInfluencedBy": {},
    }
    for edge in graph.relations.values():
        _ensure(edge.subject_type, edge.subject_id)
        _ensure(edge.object_type, edge.object_id)
        name, payload = _relation_entry(_qn(edge.subject_id), edge.predicate, _qn(edge.object_id))
        relations[name][_qn(edge.id)] = payload

    document: dict[str, Any] = {"prefix": {"ck": CK_NAMESPACE}}
    collections = [("entity", entity), ("activity", activity), ("agent", agent), *relations.items()]
    for name, collection in collections:
        if collection:
            document[name] = collection
    return document


def dumps_prov(graph: ProvenanceGraph, *, indent: int = 2) -> str:
    """Serialise a provenance graph to a PROV-JSON string.

    Args:
        graph: The graph to export.
        indent: Indentation passed to :func:`json.dumps`.

    Returns:
        The PROV-JSON document as a string.

    """
    return json.dumps(to_prov(graph), indent=indent, ensure_ascii=False)
