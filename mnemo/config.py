"""Config helpers for Mnemo."""

from __future__ import annotations

import json
import os
import platform
import socket
from pathlib import Path


CONFIG_PATH = Path(os.environ.get("MNEMO_CONFIG", str(Path.home() / ".mnemo" / "config.json")))
DEFAULT_ROOT = Path.home() / ".mnemo" / "vault"


def default_config() -> dict:
    device_id = f"{socket.gethostname().split('.')[0]}-{platform.system().lower()}"
    return {
        "vault_dir": str(DEFAULT_ROOT),
        "device_id": device_id,
        "sync": {
            "mirror_dir": "",
            "prefer_relative_paths": True,
        },
    }


def load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        config = default_config()
        save_config(config)
        return config
    except json.JSONDecodeError:
        config = default_config()
        save_config(config)
        return config


def save_config(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def resolve_vault(explicit: str | None = None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    config = load_config()
    return Path(config.get("vault_dir", str(DEFAULT_ROOT))).expanduser().resolve()
