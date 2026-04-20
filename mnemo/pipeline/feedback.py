"""Feedback review and application flow."""

from __future__ import annotations

from datetime import datetime

from mnemo.store.events import append_event
from mnemo.store.repository import materialize


def review_feedback(materialized: dict) -> dict:
    entities = materialized.get("entities", {})
    relations = materialized.get("relations", {})
    adjacency = materialized.get("adjacency", {})

    weak_entities = []
    for name, entity in entities.items():
        reasons = []
        if entity.get("confidence") == "AMBIGUOUS":
            reasons.append("ambiguous-confidence")
        if not entity.get("summary"):
            reasons.append("missing-summary")
        if len(adjacency.get(name, [])) == 0:
            reasons.append("isolated")
        if reasons:
            weak_entities.append({
                "name": name,
                "entity_type": entity.get("entity_type", "CONCEPT"),
                "confidence": entity.get("confidence", "UNKNOWN"),
                "reasons": reasons,
                "summary": entity.get("summary", "")[:180],
            })

    weak_relations = []
    for key, relation in relations.items():
        reasons = []
        if relation.get("confidence") == "AMBIGUOUS":
            reasons.append("ambiguous-confidence")
        if float(relation.get("weight", 0.0)) < 0.35:
            reasons.append("low-weight")
        if not relation.get("summary"):
            reasons.append("missing-summary")
        if reasons:
            weak_relations.append({
                "key": key,
                "source": relation.get("source", ""),
                "target": relation.get("target", ""),
                "relation_type": relation.get("relation_type", "related_to"),
                "reasons": reasons,
                "summary": relation.get("summary", "")[:180],
            })

    weak_entities.sort(key=lambda item: (len(item["reasons"]), item["name"]), reverse=True)
    weak_relations.sort(key=lambda item: (len(item["reasons"]), item["key"]), reverse=True)
    return {
        "entity_candidates": weak_entities[:20],
        "relation_candidates": weak_relations[:20],
        "recent_feedback_events": materialized.get("feedback_events", [])[-10:],
    }


def apply_feedback(paths, device_id: str, payload: dict) -> dict:
    date = payload.get("date") or datetime.utcnow().strftime("%Y-%m-%d")
    result = append_event(
        paths.events,
        {
            "event_kind": "feedback",
            "session": {
                "id": payload.get("session_id", ""),
                "date": date,
                "summary": payload.get("summary", "Applied feedback operations"),
                "workspace": payload.get("workspace", ""),
                "source": "feedback",
            },
            "operations": payload.get("operations", []),
        },
        device_id=device_id,
    )
    if result["status"] == "duplicate":
        existing = result["event"]
        return {
            "status": "duplicate",
            "reason": result["reason"],
            "event_id": existing.get("event_id", ""),
        }
    state = materialize(paths)
    return {
        "status": "ok",
        "event_id": result["event"]["event_id"],
        "applied_operations": len(payload.get("operations", [])),
        "total_entities": len(state.entities),
        "total_relations": len(state.relations),
    }
