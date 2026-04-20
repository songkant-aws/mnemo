"""Append-only event storage."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _canonicalize(value):
    if isinstance(value, dict):
        return {key: _canonicalize(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_canonicalize(item) for item in value]
    return value


def event_fingerprint(payload: dict) -> str:
    semantic = {
        key: value
        for key, value in payload.items()
        if key not in {"event_id", "recorded_at", "device_id", "schema_version", "content_fingerprint"}
    }
    canonical = json.dumps(_canonicalize(semantic), ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def ensure_event_metadata(payload: dict, device_id: str) -> dict:
    event = dict(payload)
    event.setdefault("event_id", uuid.uuid4().hex)
    event.setdefault("recorded_at", utc_now().isoformat())
    event.setdefault("device_id", device_id)
    event.setdefault("schema_version", 1)
    event.setdefault("event_kind", "capture")
    event.setdefault("content_fingerprint", event_fingerprint(event))
    return event


def event_file(root: Path, recorded_at: str, device_id: str) -> Path:
    day = recorded_at[:10]
    return root / day / f"{device_id}.jsonl"


def append_event(root: Path, payload: dict, device_id: str, dedup: bool = True) -> dict:
    event = ensure_event_metadata(payload, device_id)
    if dedup:
        existing = load_events(root)
        for current in existing:
            if current.get("event_id") == event["event_id"]:
                return {
                    "status": "duplicate",
                    "reason": "event_id",
                    "event": current,
                }
            if current.get("content_fingerprint") == event["content_fingerprint"]:
                return {
                    "status": "duplicate",
                    "reason": "content_fingerprint",
                    "event": current,
                }
    target = event_file(root, event["recorded_at"], device_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=True) + "\n")
    return {"status": "ok", "event": event}


def load_events(root: Path) -> list[dict]:
    if not root.exists():
        return []
    events: list[dict] = []
    for path in sorted(root.rglob("*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                events.append(json.loads(line))
    events.sort(key=lambda item: (item.get("recorded_at", ""), item.get("event_id", "")))
    return events


def event_inventory(root: Path) -> dict[str, list[dict]]:
    inventory: dict[str, list[dict]] = {}
    for event in load_events(root):
        fingerprint = event.get("content_fingerprint") or event_fingerprint(event)
        inventory.setdefault(fingerprint, []).append({
            "event_id": event.get("event_id", ""),
            "recorded_at": event.get("recorded_at", ""),
            "device_id": event.get("device_id", ""),
            "event_kind": event.get("event_kind", "capture"),
        })
    return inventory


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def unique(seq: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in seq:
        if item and item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered
