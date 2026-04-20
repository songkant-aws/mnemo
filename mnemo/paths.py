"""Vault path utilities."""

from __future__ import annotations

from pathlib import Path


class VaultPaths:
    def __init__(self, root: Path):
        self.root = root
        self.events = root / "events"
        self.views = root / "views"
        self.views_entities = self.views / "entities"
        self.views_daily = self.views / "daily"
        self.state = root / "state"
        self.queue = root / "queue"
        self.queue_processed = self.queue / "processed"
        self.sync = root / "sync"

    def ensure(self) -> None:
        for path in (
            self.root,
            self.events,
            self.views,
            self.views_entities,
            self.views_daily,
            self.state,
            self.queue,
            self.queue_processed,
            self.sync,
        ):
            path.mkdir(parents=True, exist_ok=True)
