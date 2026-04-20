#!/usr/bin/env python3
"""Record recent Codex write/edit activity into the Mnemo vault state.

This hook is intentionally non-invasive: it never blocks the editor workflow and
stores only a short rolling window of recent write activity. Mnemo can surface
this with `mnemo activity recent` to help later capture/review flows.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


CONFIG_PATH = Path(os.environ.get("MNEMO_CONFIG", str(Path.home() / ".mnemo" / "config.json")))
DEFAULT_VAULT = Path.home() / ".mnemo" / "vault"
ACTIVITY_FILE = "recent_codex_activity.json"
MAX_ITEMS = 50


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_vault() -> Path:
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return Path(data.get("vault_dir", str(DEFAULT_VAULT))).expanduser().resolve()
    except Exception:
        return DEFAULT_VAULT


def load_json(path: Path) -> dict:
    if not path.exists():
        return {"updated_at": "", "items": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"updated_at": "", "items": []}


def main() -> None:
    vault = load_vault()
    state_dir = vault / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    activity_path = state_dir / ACTIVITY_FILE

    try:
        payload = json.load(sys.stdin)
    except Exception:
        return

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {})
    item = {
        "recorded_at": utc_now(),
        "tool_name": tool_name,
        "file_path": tool_input.get("file_path", ""),
        "old_string_preview": str(tool_input.get("old_string", ""))[:120],
        "new_string_preview": str(tool_input.get("new_string", ""))[:120],
    }

    existing = load_json(activity_path)
    items = existing.get("items", [])
    items.append(item)
    items = items[-MAX_ITEMS:]
    activity_path.write_text(
        json.dumps({"updated_at": item["recorded_at"], "items": items}, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
