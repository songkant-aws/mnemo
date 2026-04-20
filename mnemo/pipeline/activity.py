"""Recent Codex activity helpers."""

from __future__ import annotations

import json
from pathlib import Path


ACTIVITY_FILE = "recent_codex_activity.json"


def activity_path(paths) -> Path:
    return paths.state / ACTIVITY_FILE


def load_recent_activity(paths) -> dict:
    path = activity_path(paths)
    if not path.exists():
        return {"updated_at": "", "items": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"updated_at": "", "items": []}
