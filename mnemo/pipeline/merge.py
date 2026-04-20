"""Merge suggestion and application flow."""

from __future__ import annotations

from datetime import datetime
from difflib import SequenceMatcher

from mnemo.models import normalize_name
from mnemo.store.events import append_event
from mnemo.store.repository import materialize


def _token_set(name: str) -> set[str]:
    return {token for token in normalize_name(name).split("_") if len(token) >= 3}


def suggest_merges(materialized: dict, limit: int = 20) -> list[dict]:
    entities = materialized.get("entities", {})
    names = sorted(entities)
    candidates: list[dict] = []
    for index, left in enumerate(names):
        left_tokens = _token_set(left)
        left_type = entities[left].get("entity_type", "")
        for right in names[index + 1:]:
            if left_type and entities[right].get("entity_type", "") and left_type != entities[right].get("entity_type", ""):
                continue
            right_tokens = _token_set(right)
            shared = sorted(left_tokens & right_tokens)
            ratio = SequenceMatcher(None, left, right).ratio()
            prefix_bonus = 0.2 if left.startswith(right) or right.startswith(left) else 0.0
            subset_bonus = 0.15 if left_tokens and right_tokens and (left_tokens <= right_tokens or right_tokens <= left_tokens) else 0.0
            if not shared and ratio < 0.72:
                continue
            score = ratio + (0.15 * len(shared)) + prefix_bonus + subset_bonus
            if score < 0.78:
                continue
            candidates.append({
                "score": round(score, 3),
                "canonical_hint": min(left, right, key=len),
                "entities": [left, right],
                "shared_tokens": shared,
                "left_summary": entities[left].get("summary", "")[:140],
                "right_summary": entities[right].get("summary", "")[:140],
            })
    candidates.sort(key=lambda item: (-item["score"], item["entities"]))
    return candidates[:limit]


def apply_merges(paths, device_id: str, payload: dict) -> dict:
    date = payload.get("date") or datetime.utcnow().strftime("%Y-%m-%d")
    result = append_event(
        paths.events,
        {
            "event_kind": "merge",
            "session": {
                "id": payload.get("session_id", ""),
                "date": date,
                "summary": payload.get("summary", "Applied merge directives"),
                "workspace": payload.get("workspace", ""),
                "source": "merge",
            },
            "merges": payload.get("merges", []),
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
        "applied_merges": payload.get("merges", []),
        "total_entities": len(state.entities),
    }
