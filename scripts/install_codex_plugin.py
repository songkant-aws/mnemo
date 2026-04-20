#!/usr/bin/env python3
"""One-click installer for the local Mnemo Codex plugin."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path


PLUGIN_NAME = "mnemo"
MARKETPLACE_NAME = "songkant-local"
MARKETPLACE_DISPLAY_NAME = "Songkant Local"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def source_plugin_dir(root: Path) -> Path:
    return root / "codex_plugin"


def target_plugin_dir() -> Path:
    return Path.home() / "plugins" / PLUGIN_NAME


def marketplace_path() -> Path:
    return Path.home() / ".agents" / "plugins" / "marketplace.json"


def copy_plugin_tree(source: Path, target: Path, root: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)

    wrapper = target / "scripts" / "mnemo"
    wrapper_text = wrapper.read_text(encoding="utf-8").replace("__MNEMO_REPO_ROOT__", str(root))
    wrapper.write_text(wrapper_text, encoding="utf-8")

    for path in target.rglob("*"):
        if path.is_file() and path.suffix in {"", ".py"}:
            mode = path.stat().st_mode
            path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def update_marketplace(path: Path) -> None:
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = {
            "name": MARKETPLACE_NAME,
            "interface": {"displayName": MARKETPLACE_DISPLAY_NAME},
            "plugins": [],
        }

    payload["name"] = payload.get("name") or MARKETPLACE_NAME
    payload.setdefault("interface", {})
    payload["interface"]["displayName"] = payload["interface"].get("displayName") or MARKETPLACE_DISPLAY_NAME
    payload.setdefault("plugins", [])

    entry = {
        "name": PLUGIN_NAME,
        "source": {
            "source": "local",
            "path": f"./plugins/{PLUGIN_NAME}",
        },
        "policy": {
            "installation": "AVAILABLE",
            "authentication": "ON_INSTALL",
        },
        "category": "Productivity",
    }

    replaced = False
    for index, current in enumerate(payload["plugins"]):
        if isinstance(current, dict) and current.get("name") == PLUGIN_NAME:
            payload["plugins"][index] = entry
            replaced = True
            break
    if not replaced:
        payload["plugins"].append(entry)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def ensure_vault_initialized(root: Path) -> None:
    config_path = Path.home() / ".mnemo" / "config.json"
    if config_path.exists():
        return
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root)
    subprocess.run(
        ["python3", "-m", "mnemo.cli", "init"],
        cwd=str(root),
        env=env,
        check=True,
    )


def main() -> None:
    root = repo_root()
    source = source_plugin_dir(root)
    target = target_plugin_dir()
    copy_plugin_tree(source, target, root)
    update_marketplace(marketplace_path())
    ensure_vault_initialized(root)

    print(json.dumps({
        "status": "ok",
        "plugin_dir": str(target),
        "marketplace": str(marketplace_path()),
        "next_steps": [
            "Restart or refresh Codex so it reloads local plugins.",
            "Use ~/plugins/mnemo/scripts/mnemo --help to verify the runtime.",
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
