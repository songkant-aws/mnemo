"""Sync health checks across local and mirror vaults."""

from __future__ import annotations

from pathlib import Path

from mnemo.store.events import event_inventory
from mnemo.sync.mirror import build_manifest


def sync_health(local: Path, mirror: Path) -> dict:
    local = local.resolve()
    mirror = mirror.resolve()

    local_manifest = build_manifest(local) if local.exists() else {}
    mirror_manifest = build_manifest(mirror) if mirror.exists() else {}

    local_files = set(local_manifest)
    mirror_files = set(mirror_manifest)
    local_only = sorted(local_files - mirror_files)
    mirror_only = sorted(mirror_files - local_files)
    divergent = sorted(
        rel for rel in (local_files & mirror_files)
        if local_manifest[rel]["sha256"] != mirror_manifest[rel]["sha256"]
    )

    local_events = event_inventory(local / "events") if (local / "events").exists() else {}
    mirror_events = event_inventory(mirror / "events") if (mirror / "events").exists() else {}
    local_event_only = sorted(set(local_events) - set(mirror_events))
    mirror_event_only = sorted(set(mirror_events) - set(local_events))

    duplicate_fingerprints = []
    for fingerprint in sorted(set(local_events) | set(mirror_events)):
        local_entries = local_events.get(fingerprint, [])
        mirror_entries = mirror_events.get(fingerprint, [])
        event_ids = {item.get("event_id", "") for item in (local_entries + mirror_entries) if item.get("event_id", "")}
        if len(event_ids) > 1:
            duplicate_fingerprints.append({
                "fingerprint": fingerprint,
                "count": len(event_ids),
                "local": local_entries,
                "mirror": mirror_entries,
            })

    event_divergence = bool(local_event_only or mirror_event_only or duplicate_fingerprints)

    if divergent:
        recommendation = "inspect-divergence-before-sync"
    elif event_divergence and local_event_only:
        recommendation = "push-local-to-mirror"
    elif event_divergence and mirror_event_only:
        recommendation = "pull-mirror-to-local"
    elif event_divergence and duplicate_fingerprints:
        recommendation = "deduplicate-events-before-sync"
    elif local_only or mirror_only:
        recommendation = "rebuild-or-sync-derived-files"
    else:
        recommendation = "healthy"

    return {
        "status": "ok",
        "local": str(local),
        "mirror": str(mirror),
        "files": {
            "local_only": local_only[:50],
            "mirror_only": mirror_only[:50],
            "divergent": divergent[:50],
        },
        "events": {
            "local_only_fingerprints": local_event_only[:50],
            "mirror_only_fingerprints": mirror_event_only[:50],
            "duplicate_fingerprints": duplicate_fingerprints[:20],
        },
        "recommendation": recommendation,
    }
