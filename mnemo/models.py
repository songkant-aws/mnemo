"""Data models used by Mnemo."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def normalize_name(value: str) -> str:
    return "_".join(part for part in value.strip().upper().replace("-", "_").split() if part)


@dataclass
class Entity:
    name: str
    entity_type: str = "CONCEPT"
    summary: str = ""
    confidence: str = "EXTRACTED"
    aliases: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    paths: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    session_ids: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    first_seen: str = ""
    last_seen: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "entity_type": self.entity_type,
            "summary": self.summary,
            "confidence": self.confidence,
            "aliases": self.aliases,
            "urls": self.urls,
            "paths": self.paths,
            "evidence": self.evidence,
            "session_ids": self.session_ids,
            "tags": self.tags,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
        }


@dataclass
class Relation:
    source: str
    target: str
    relation_type: str = "related_to"
    summary: str = ""
    weight: float = 0.5
    confidence: str = "EXTRACTED"
    evidence: list[str] = field(default_factory=list)
    session_ids: list[str] = field(default_factory=list)
    first_seen: str = ""
    last_seen: str = ""

    def key(self) -> str:
        left, right = sorted((normalize_name(self.source), normalize_name(self.target)))
        return f"{left}::{self.relation_type}::{right}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "relation_type": self.relation_type,
            "summary": self.summary,
            "weight": self.weight,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "session_ids": self.session_ids,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
        }
