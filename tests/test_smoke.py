"""Basic smoke coverage for Mnemo using stdlib only."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mnemo.paths import VaultPaths
from mnemo.pipeline.capture import capture
from mnemo.pipeline.feedback import apply_feedback, review_feedback
from mnemo.pipeline.merge import apply_merges, suggest_merges
from mnemo.pipeline.query import query
from mnemo.pipeline.queue import consume_queue, queue_status
from mnemo.store.repository import load_materialized
from mnemo.sync.health import sync_health
from mnemo.sync.mirror import mirror_vault


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        local_paths = VaultPaths(root / "vault")
        local_paths.ensure()

        result = capture(
            local_paths,
            device_id="test-device",
            payload={
                "session": {"id": "sess-1", "date": "2026-04-20", "summary": "Fixed the planner bug"},
                "entities": [
                    {"name": "planner", "entity_type": "project", "description": "Main planning module"},
                    {"name": "queue dedup", "entity_type": "concept", "description": "Avoid duplicate queue events"},
                    {"name": "planner module", "entity_type": "project", "description": "Alias-like planner name"},
                ],
                "relations": [
                    {"source": "planner", "target": "queue dedup", "description": "implements", "weight": 0.9},
                ],
            },
        )
        assert result["status"] == "ok"

        duplicate = capture(
            local_paths,
            device_id="test-device",
            payload={
                "session": {"id": "sess-1", "date": "2026-04-20", "summary": "Fixed the planner bug"},
                "entities": [
                    {"name": "planner", "entity_type": "project", "description": "Main planning module"},
                    {"name": "queue dedup", "entity_type": "concept", "description": "Avoid duplicate queue events"},
                    {"name": "planner module", "entity_type": "project", "description": "Alias-like planner name"},
                ],
                "relations": [
                    {"source": "planner", "target": "queue dedup", "description": "implements", "weight": 0.9},
                ],
            },
        )
        assert duplicate["status"] == "duplicate"

        materialized = load_materialized(local_paths)
        found = query(materialized, "planner dedup")
        assert "PLANNER" in found["matched_entities"]
        assert found["relations"]
        planner_note = local_paths.obsidian_entities / "PLANNER.md"
        daily_note = local_paths.obsidian_daily / "2026-04-20.md"
        home_note = local_paths.obsidian / "Home.md"
        assert planner_note.exists()
        assert daily_note.exists()
        assert home_note.exists()
        assert "[[entities/QUEUE_DEDUP|QUEUE_DEDUP]]" in planner_note.read_text(encoding="utf-8")
        assert "[[entities/PLANNER|PLANNER]]" in daily_note.read_text(encoding="utf-8")

        queue_payload = {
            "captured_at": "2026-04-20T08:00:00Z",
            "session_id": "queued-1",
            "stop_reason": "user_exit",
            "payload": {
                "cwd": str(root / "workspace-a"),
                "last_user_message": "please wire up sync health",
                "last_assistant_message": "Implemented queue handling and sync health checks",
                "tool_calls": [{"tool_name": "Read"}],
            },
        }
        (local_paths.queue / "queued-1.json").write_text(json.dumps(queue_payload, indent=2) + "\n", encoding="utf-8")
        queue_result = consume_queue(local_paths, device_id="test-device")
        assert queue_result["consumed"] == 1
        assert queue_status(local_paths)["pending_count"] == 0

        materialized = load_materialized(local_paths)
        found = query(materialized, "sync health")
        assert found["matched_sessions"]

        merges = suggest_merges(materialized)
        assert any(set(item["entities"]) == {"PLANNER", "PLANNER_MODULE"} for item in merges)

        merge_result = apply_merges(
            local_paths,
            device_id="test-device",
            payload={"merges": [{"canonical": "PLANNER", "aliases": ["PLANNER_MODULE"]}]},
        )
        assert merge_result["status"] == "ok"

        feedback_result = apply_feedback(
            local_paths,
            device_id="test-device",
            payload={
                "operations": [
                    {
                        "action": "update_entity",
                        "name": "PLANNER",
                        "summary": "Planner with queue dedup and sync health support.",
                        "add_aliases": ["Task Planner"],
                    }
                ]
            },
        )
        assert feedback_result["status"] == "ok"

        materialized = load_materialized(local_paths)
        review = review_feedback(materialized)
        assert "recent_feedback_events" in review

        mirror_root = root / "mirror"
        mirror_result = mirror_vault(local_paths.root, mirror_root)
        assert mirror_result["status"] == "ok"
        health = sync_health(local_paths.root, mirror_root)
        assert health["status"] == "ok"

        print(json.dumps({
            "status": "ok",
            "matched_entities": found["matched_entities"],
            "queue_processed": queue_result["consumed"],
            "merge_count": len(merge_result["applied_merges"]),
        }, indent=2))


if __name__ == "__main__":
    main()
