"""Sync helpers.

Mnemo intentionally keeps canonical state in plain files. The safest multi-device
strategy is to store the vault inside a cloud-synced directory. When that is not
practical, this mirror command copies the vault into a sync folder managed by
Dropbox, iCloud Drive, OneDrive, Google Drive, or Syncthing.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


def file_digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def build_manifest(root: Path) -> dict[str, dict]:
    manifest: dict[str, dict] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        manifest[rel] = {
            "sha256": file_digest(path),
            "size": path.stat().st_size,
        }
    return manifest


def mirror_vault(source: Path, target: Path) -> dict:
    source = source.resolve()
    target = target.resolve()
    if str(target).startswith(str(source) + "/"):
        raise ValueError("mirror target must not live inside the source vault")
    if str(source).startswith(str(target) + "/"):
        raise ValueError("mirror target must not be a parent of the source vault")
    target.mkdir(parents=True, exist_ok=True)
    copied = 0
    source_manifest = build_manifest(source)
    target_manifest = build_manifest(target) if target.exists() else {}

    for rel, meta in source_manifest.items():
        if target_manifest.get(rel, {}).get("sha256") == meta["sha256"]:
            continue
        src = source / rel
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied += 1

    manifest_path = target / ".mnemo-sync-manifest.json"
    manifest_path.write_text(json.dumps(source_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "status": "ok",
        "source": str(source),
        "target": str(target),
        "files_considered": len(source_manifest),
        "files_copied": copied,
        "manifest": str(manifest_path),
    }
