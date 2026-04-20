"""Queue inspection and auto-consumption."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from mnemo.pipeline.capture import capture


def queue_files(paths, include_processed: bool = False) -> list[Path]:
    items = []
    for path in sorted(paths.queue.glob("*.json")):
        if path.is_file():
            items.append(path)
    if include_processed:
        for path in sorted(paths.queue_processed.glob("*.json")):
            if path.is_file():
                items.append(path)
    return items


def queue_status(paths) -> dict:
    pending = []
    for path in queue_files(paths):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        pending.append({
            "file": path.name,
            "session_id": payload.get("session_id", ""),
            "captured_at": payload.get("captured_at", ""),
            "stop_reason": payload.get("stop_reason", ""),
        })
    processed = []
    for path in sorted(paths.queue_processed.glob("*.json"))[-20:]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        processed.append({
            "file": path.name,
            "session_id": payload.get("session_id", ""),
            "captured_at": payload.get("captured_at", ""),
        })
    return {
        "pending_count": len(pending),
        "pending": pending[:20],
        "processed_count": len(list(paths.queue_processed.glob("*.json"))),
        "recent_processed": processed,
    }


def _first_nonempty(mapping: dict, *keys: str) -> str:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _tool_names(payload: dict) -> list[str]:
    found = []
    for item in payload.get("tool_calls", []):
        name = item.get("tool_name") or item.get("name")
        if isinstance(name, str) and name.strip():
            found.append(name.strip())
    for item in payload.get("tools", []):
        if isinstance(item, str) and item.strip():
            found.append(item.strip())
    return sorted(dict.fromkeys(found))


def _payload_to_capture_payload(breadcrumb: dict) -> dict:
    payload = breadcrumb.get("payload", {})
    workspace = _first_nonempty(payload, "cwd", "workspace", "working_directory")
    last_assistant = _first_nonempty(payload, "last_assistant_message")
    last_user = _first_nonempty(payload, "last_user_message")
    summary = last_assistant or last_user or f"Session stopped with reason: {breadcrumb.get('stop_reason', 'unknown')}"
    summary = summary.replace("\n", " ").strip()[:400]
    session_id = breadcrumb.get("session_id", "")
    captured_at = breadcrumb.get("captured_at", datetime.utcnow().isoformat() + "Z")
    date = captured_at[:10]

    notes = []
    if last_user:
        notes.append(f"Last user message: {last_user[:300]}")
    if last_assistant:
        notes.append(f"Last assistant message: {last_assistant[:300]}")
    if breadcrumb.get("stop_reason"):
        notes.append(f"Stop reason: {breadcrumb['stop_reason']}")
    transcript_path = _first_nonempty(payload, "transcript_path")
    if transcript_path:
        notes.append(f"Transcript: {transcript_path}")

    entities = []
    if workspace:
        project_name = Path(workspace).name
        entities.append({
            "name": project_name,
            "entity_type": "PROJECT",
            "description": f"Workspace captured from queue auto-consume for session {session_id}",
            "confidence": "INFERRED",
            "local_path": workspace,
        })
    for tool_name in _tool_names(payload):
        entities.append({
            "name": tool_name,
            "entity_type": "TOOL",
            "description": f"Tool observed in queued Claude Code session {session_id}",
            "confidence": "INFERRED",
        })

    return {
        "event_kind": "capture",
        "session": {
            "id": session_id,
            "date": date,
            "summary": summary,
            "workspace": workspace,
            "source": "queue-auto",
        },
        "entities": entities,
        "relations": [],
        "notes": notes,
    }


def consume_queue(paths, device_id: str, limit: int | None = None) -> dict:
    pending = queue_files(paths)
    if limit is not None:
        pending = pending[:limit]
    processed = []
    duplicates = []
    for path in pending:
        try:
            breadcrumb = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        result = capture(paths, device_id=device_id, payload=_payload_to_capture_payload(breadcrumb))
        target = paths.queue_processed / path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.replace(target)
        except FileNotFoundError:
            if not target.exists():
                raise
        if result["status"] == "duplicate":
            duplicates.append({"file": path.name, "reason": result["reason"]})
        else:
            processed.append({"file": path.name, "session_id": result["session_id"], "event_id": result["event_id"]})
    return {
        "status": "ok",
        "consumed": len(processed),
        "duplicates": duplicates,
        "processed": processed,
    }
