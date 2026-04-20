"""Status helpers."""

from __future__ import annotations

from collections import Counter

from mnemo.pipeline.activity import load_recent_activity


def build_status(materialized: dict, vault_root: str, sync_config: dict, recent_activity: dict | None = None) -> dict:
    entities = materialized.get("entities", {})
    relations = materialized.get("relations", {})
    sessions = materialized.get("sessions", {})
    type_counter = Counter(item.get("entity_type", "UNKNOWN") for item in entities.values())
    confidence_counter = Counter(item.get("confidence", "UNKNOWN") for item in entities.values())
    hubs = []
    adjacency = materialized.get("adjacency", {})
    for name, neighbors in adjacency.items():
        hubs.append({"name": name, "degree": len(neighbors)})
    hubs.sort(key=lambda item: (-item["degree"], item["name"]))
    activity = recent_activity or {"updated_at": "", "items": []}
    return {
        "vault_dir": vault_root,
        "entity_count": len(entities),
        "relation_count": len(relations),
        "session_count": len(sessions),
        "types": dict(sorted(type_counter.items())),
        "confidence": dict(sorted(confidence_counter.items())),
        "top_hubs": hubs[:10],
        "sync": sync_config,
        "recent_activity": {
            "updated_at": activity.get("updated_at", ""),
            "count": len(activity.get("items", [])),
            "items": activity.get("items", [])[:10],
        },
    }
