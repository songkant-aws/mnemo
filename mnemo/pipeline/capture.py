"""Capture ingestion workflow."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from mnemo.store.events import append_event
from mnemo.store.repository import materialize


def normalize_capture_payload(payload: dict) -> dict:
    session = payload.get("session", {})
    date = session.get("date") or payload.get("date") or datetime.now().strftime("%Y-%m-%d")
    summary = session.get("summary") or payload.get("daily_summary", "")
    session_id = session.get("id")
    if not session_id:
        stable = json.dumps(
            {
                "date": date,
                "summary": summary,
                "entities": [item.get("name", "") for item in payload.get("entities", [])],
            },
            sort_keys=True,
        )
        session_id = hashlib.sha1(stable.encode("utf-8")).hexdigest()[:12]
    return {
        "event_kind": payload.get("event_kind", "capture"),
        "session": {
            "id": session_id,
            "date": date,
            "summary": summary,
            "workspace": session.get("workspace", payload.get("workspace", "")),
            "source": session.get("source", payload.get("source", "manual")),
        },
        "entities": payload.get("entities", []),
        "relations": payload.get("relations", []),
        "notes": payload.get("notes", []),
    }


def capture(paths, device_id: str, payload: dict) -> dict:
    normalized = normalize_capture_payload(payload)
    result = append_event(paths.events, normalized, device_id=device_id)
    if result["status"] == "duplicate":
        existing = result["event"]
        return {
            "status": "duplicate",
            "reason": result["reason"],
            "event_id": existing.get("event_id", ""),
            "recorded_at": existing.get("recorded_at", ""),
            "session_id": (existing.get("session") or {}).get("id", ""),
        }
    event = result["event"]
    state = materialize(paths)
    return {
        "status": "ok",
        "event_id": event["event_id"],
        "session_id": normalized["session"]["id"],
        "recorded_at": event["recorded_at"],
        "entity_count": len(normalized["entities"]),
        "relation_count": len(normalized["relations"]),
        "total_entities": len(state.entities),
        "total_relations": len(state.relations),
        "daily_view": str(paths.views_daily / f"{normalized['session']['date']}.md"),
    }
