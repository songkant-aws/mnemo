"""Materialize Mnemo events into queryable state and Markdown views."""

from __future__ import annotations

import json
import re
from collections import defaultdict

from mnemo.models import Entity, Relation, normalize_name
from mnemo.paths import VaultPaths
from mnemo.store.events import load_events, unique, write_json


SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")
OBSIDIAN_NOTE_RE = re.compile(r'[\\/:#\^\[\]\|*?"<>]+')


def slugify(value: str) -> str:
    return SAFE_NAME_RE.sub("-", value.strip()).strip("-").lower() or "unknown"


def obsidian_note_name(value: str) -> str:
    return OBSIDIAN_NOTE_RE.sub("_", value.strip()) or "unknown"


def prune_markdown_dir(root, keep_names: set[str]) -> None:
    for path in root.glob("*.md"):
        if path.name not in keep_names:
            path.unlink()


def confidence_rank(value: str) -> int:
    return {"AMBIGUOUS": 0, "INFERRED": 1, "EXTRACTED": 2}.get((value or "").upper(), 0)


def resolve_name(name: str, redirects: dict[str, str]) -> str:
    current = normalize_name(name)
    seen = set()
    while current in redirects and current not in seen:
        seen.add(current)
        current = redirects[current]
    return current


class MaterializedState:
    def __init__(
        self,
        entities: dict[str, Entity],
        relations: dict[str, Relation],
        sessions: dict[str, dict],
        redirects: dict[str, str],
        duplicates: list[dict],
        feedback_events: list[dict],
    ):
        self.entities = entities
        self.relations = relations
        self.sessions = sessions
        self.redirects = redirects
        self.duplicates = duplicates
        self.feedback_events = feedback_events

    def to_dict(self) -> dict:
        adjacency: dict[str, list[str]] = defaultdict(list)
        relation_summaries: dict[str, list[str]] = defaultdict(list)
        for relation in self.relations.values():
            left = normalize_name(relation.source)
            right = normalize_name(relation.target)
            adjacency[left].append(right)
            adjacency[right].append(left)
            if relation.summary:
                relation_summaries[left].append(relation.summary)
                relation_summaries[right].append(relation.summary)
        return {
            "entities": {name: entity.to_dict() for name, entity in sorted(self.entities.items())},
            "relations": {key: relation.to_dict() for key, relation in sorted(self.relations.items())},
            "sessions": dict(sorted(self.sessions.items())),
            "adjacency": {name: sorted(unique(neighbors)) for name, neighbors in sorted(adjacency.items())},
            "relation_summaries": {name: unique(values) for name, values in sorted(relation_summaries.items())},
            "redirects": dict(sorted(self.redirects.items())),
            "duplicates": self.duplicates,
            "feedback_events": self.feedback_events,
        }


def normalize_entity(raw: dict, session_id: str, recorded_at: str) -> Entity:
    name = normalize_name(raw.get("name", ""))
    return Entity(
        name=name,
        entity_type=raw.get("entity_type", "CONCEPT").upper(),
        summary=raw.get("summary") or raw.get("description", ""),
        confidence=raw.get("confidence", "EXTRACTED").upper(),
        aliases=raw.get("aliases", []),
        urls=unique([raw.get("url", "")] + raw.get("references", []) + raw.get("urls", [])),
        paths=unique([raw.get("local_path", "")] + raw.get("paths", [])),
        evidence=raw.get("evidence", []),
        session_ids=[session_id],
        tags=raw.get("tags", []),
        first_seen=recorded_at[:10],
        last_seen=recorded_at[:10],
    )


def normalize_relation(raw: dict, session_id: str, recorded_at: str) -> Relation:
    return Relation(
        source=normalize_name(raw.get("source", "")),
        target=normalize_name(raw.get("target", "")),
        relation_type=raw.get("relation_type", raw.get("type", "related_to")),
        summary=raw.get("summary") or raw.get("description", ""),
        weight=float(raw.get("weight", 0.5)),
        confidence=raw.get("confidence", "EXTRACTED").upper(),
        evidence=raw.get("evidence", []),
        session_ids=[session_id],
        first_seen=recorded_at[:10],
        last_seen=recorded_at[:10],
    )


def merge_entity(current: Entity, incoming: Entity) -> Entity:
    current.summary = incoming.summary or current.summary
    current.entity_type = incoming.entity_type or current.entity_type
    if confidence_rank(incoming.confidence) > confidence_rank(current.confidence):
        current.confidence = incoming.confidence
    current.aliases = unique(current.aliases + incoming.aliases)
    current.urls = unique(current.urls + incoming.urls)
    current.paths = unique(current.paths + incoming.paths)
    current.evidence = unique(current.evidence + incoming.evidence)
    current.session_ids = unique(current.session_ids + incoming.session_ids)
    current.tags = unique(current.tags + incoming.tags)
    current.first_seen = min(filter(None, [current.first_seen, incoming.first_seen]), default="")
    current.last_seen = max(filter(None, [current.last_seen, incoming.last_seen]), default="")
    return current


def merge_relation(current: Relation, incoming: Relation) -> Relation:
    current.summary = incoming.summary or current.summary
    current.weight = max(current.weight, incoming.weight)
    if confidence_rank(incoming.confidence) > confidence_rank(current.confidence):
        current.confidence = incoming.confidence
    current.evidence = unique(current.evidence + incoming.evidence)
    current.session_ids = unique(current.session_ids + incoming.session_ids)
    current.first_seen = min(filter(None, [current.first_seen, incoming.first_seen]), default="")
    current.last_seen = max(filter(None, [current.last_seen, incoming.last_seen]), default="")
    return current


def relation_key(source: str, target: str, relation_type: str) -> str:
    left, right = sorted((normalize_name(source), normalize_name(target)))
    return f"{left}::{relation_type}::{right}"


def upsert_relation_map(relation_map: dict[str, Relation], relation: Relation) -> None:
    key = relation_key(relation.source, relation.target, relation.relation_type)
    if key in relation_map:
        relation_map[key] = merge_relation(relation_map[key], relation)
    else:
        relation_map[key] = relation


def apply_merge(
    entity_map: dict[str, Entity],
    relation_map: dict[str, Relation],
    redirects: dict[str, str],
    canonical: str,
    aliases: list[str],
) -> None:
    canonical_name = resolve_name(canonical, redirects)
    if canonical_name not in entity_map:
        entity_map[canonical_name] = Entity(name=canonical_name)

    for alias in aliases:
        alias_name = resolve_name(alias, redirects)
        if not alias_name or alias_name == canonical_name:
            continue
        redirects[alias_name] = canonical_name
        if alias_name in entity_map:
            alias_entity = entity_map.pop(alias_name)
            alias_entity.aliases = unique(alias_entity.aliases + [alias_name])
            entity_map[canonical_name] = merge_entity(entity_map[canonical_name], alias_entity)
        entity_map[canonical_name].aliases = unique(entity_map[canonical_name].aliases + [alias_name])

    rebuilt: dict[str, Relation] = {}
    for relation in relation_map.values():
        relation.source = resolve_name(relation.source, redirects)
        relation.target = resolve_name(relation.target, redirects)
        if relation.source == relation.target:
            continue
        upsert_relation_map(rebuilt, relation)
    relation_map.clear()
    relation_map.update(rebuilt)


def apply_feedback(
    entity_map: dict[str, Entity],
    relation_map: dict[str, Relation],
    redirects: dict[str, str],
    operations: list[dict],
) -> None:
    for op in operations:
        action = op.get("action", "").lower()
        if action == "update_entity":
            name = resolve_name(op.get("name", ""), redirects)
            if not name:
                continue
            entity = entity_map.get(name) or Entity(name=name)
            if op.get("summary"):
                entity.summary = op["summary"]
            if op.get("entity_type"):
                entity.entity_type = op["entity_type"].upper()
            if op.get("confidence"):
                entity.confidence = op["confidence"].upper()
            entity.aliases = unique(entity.aliases + op.get("add_aliases", []))
            entity.tags = unique(entity.tags + op.get("add_tags", []))
            entity.urls = unique(entity.urls + op.get("add_urls", []))
            entity.paths = unique(entity.paths + op.get("add_paths", []))
            entity_map[name] = entity
        elif action == "delete_entity":
            name = resolve_name(op.get("name", ""), redirects)
            if name in entity_map:
                entity_map.pop(name, None)
                relation_map_copy = list(relation_map.items())
                for key, relation in relation_map_copy:
                    if relation.source == name or relation.target == name:
                        relation_map.pop(key, None)
        elif action == "update_relation":
            source = resolve_name(op.get("source", ""), redirects)
            target = resolve_name(op.get("target", ""), redirects)
            rel_type = op.get("relation_type", "related_to")
            if not source or not target or source == target:
                continue
            key = relation_key(source, target, rel_type)
            relation = relation_map.get(key) or Relation(source=source, target=target, relation_type=rel_type)
            if op.get("summary"):
                relation.summary = op["summary"]
            if op.get("confidence"):
                relation.confidence = op["confidence"].upper()
            if "weight" in op:
                relation.weight = float(op["weight"])
            relation_map[key] = relation
        elif action == "delete_relation":
            source = resolve_name(op.get("source", ""), redirects)
            target = resolve_name(op.get("target", ""), redirects)
            rel_type = op.get("relation_type", "related_to")
            relation_map.pop(relation_key(source, target, rel_type), None)


def materialize(paths: VaultPaths) -> MaterializedState:
    entity_map: dict[str, Entity] = {}
    relation_map: dict[str, Relation] = {}
    sessions: dict[str, dict] = {}
    redirects: dict[str, str] = {}
    duplicates: list[dict] = []
    feedback_events: list[dict] = []

    seen_ids: set[str] = set()
    seen_fingerprints: dict[str, str] = {}

    for event in load_events(paths.events):
        event_id = event.get("event_id", "")
        fingerprint = event.get("content_fingerprint", "")
        if event_id and event_id in seen_ids:
            duplicates.append({"event_id": event_id, "reason": "event_id"})
            continue
        if fingerprint and fingerprint in seen_fingerprints:
            duplicates.append({
                "event_id": event_id,
                "reason": "content_fingerprint",
                "duplicate_of": seen_fingerprints[fingerprint],
            })
            continue
        if event_id:
            seen_ids.add(event_id)
        if fingerprint:
            seen_fingerprints[fingerprint] = event_id or fingerprint

        session = event.get("session", {})
        session_id = session.get("id") or event_id
        recorded_at = event.get("recorded_at", "")
        session_entry = sessions.get(session_id, {
            "id": session_id,
            "date": session.get("date") or recorded_at[:10],
            "summary": session.get("summary") or event.get("daily_summary", ""),
            "workspace": session.get("workspace", ""),
            "source": session.get("source", "capture"),
            "recorded_at": recorded_at,
            "device_id": event.get("device_id", ""),
            "entities": [],
            "notes": [],
        })
        session_entry["date"] = session.get("date") or session_entry.get("date", recorded_at[:10])
        session_entry["summary"] = session.get("summary") or session_entry.get("summary", "")
        session_entry["workspace"] = session.get("workspace") or session_entry.get("workspace", "")
        session_entry["source"] = session.get("source") or session_entry.get("source", "capture")
        session_entry["recorded_at"] = recorded_at or session_entry.get("recorded_at", "")
        session_entry["device_id"] = event.get("device_id", session_entry.get("device_id", ""))
        session_entry["notes"] = unique(session_entry.get("notes", []) + event.get("notes", []))
        sessions[session_id] = session_entry

        kind = event.get("event_kind", "capture")
        if kind == "merge":
            for merge in event.get("merges", []):
                apply_merge(entity_map, relation_map, redirects, merge.get("canonical", ""), merge.get("aliases", []))
            continue
        if kind == "feedback":
            feedback_events.append({
                "event_id": event_id,
                "recorded_at": recorded_at,
                "operations": event.get("operations", []),
            })
            apply_feedback(entity_map, relation_map, redirects, event.get("operations", []))
            continue

        for raw in event.get("entities", []):
            entity = normalize_entity(raw, session_id, recorded_at)
            if not entity.name:
                continue
            entity.name = resolve_name(entity.name, redirects)
            sessions[session_id]["entities"] = unique(session_entry.get("entities", []) + [entity.name])
            if entity.name in entity_map:
                entity_map[entity.name] = merge_entity(entity_map[entity.name], entity)
            else:
                entity_map[entity.name] = entity

        for raw in event.get("relations", []):
            relation = normalize_relation(raw, session_id, recorded_at)
            relation.source = resolve_name(relation.source, redirects)
            relation.target = resolve_name(relation.target, redirects)
            if not relation.source or not relation.target or relation.source == relation.target:
                continue
            upsert_relation_map(relation_map, relation)

    state = MaterializedState(entity_map, relation_map, sessions, redirects, duplicates, feedback_events)
    write_json(paths.state / "materialized.json", state.to_dict())
    export_views(paths, state)
    return state


def export_views(paths: VaultPaths, state: MaterializedState) -> None:
    adjacency: dict[str, list[Relation]] = defaultdict(list)
    for relation in state.relations.values():
        adjacency[relation.source].append(relation)
        adjacency[relation.target].append(relation)

    keep_entity_views: set[str] = set()
    for entity in state.entities.values():
        filename = f"{slugify(entity.name)}.md"
        keep_entity_views.add(filename)
        path = paths.views_entities / filename
        lines = [
            "---",
            f'name: "{entity.name}"',
            f'entity_type: "{entity.entity_type}"',
            f'confidence: "{entity.confidence}"',
            f'first_seen: "{entity.first_seen}"',
            f'last_seen: "{entity.last_seen}"',
            f"session_count: {len(entity.session_ids)}",
            "---",
            "",
            f"# {entity.name}",
            "",
            entity.summary or "_No summary yet._",
            "",
        ]
        if entity.aliases:
            lines += ["## Aliases", ""] + [f"- {alias}" for alias in entity.aliases] + [""]
        if entity.urls:
            lines += ["## References", ""] + [f"- {url}" for url in entity.urls] + [""]
        if entity.paths:
            lines += ["## Local Paths", ""] + [f"- `{value}`" for value in entity.paths] + [""]
        related = sorted(adjacency.get(entity.name, []), key=lambda item: (-item.weight, item.target))
        if related:
            lines += ["## Relations", ""]
            for relation in related:
                other = relation.target if relation.source == entity.name else relation.source
                lines.append(
                    f"- `{relation.relation_type}` [[{other}]] ({relation.confidence}, weight={relation.weight:.2f})"
                )
            lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")

    by_day: dict[str, list[dict]] = defaultdict(list)
    for session in state.sessions.values():
        by_day[session["date"]].append(session)
    keep_daily_views: set[str] = set()
    for day, sessions in by_day.items():
        filename = f"{day}.md"
        keep_daily_views.add(filename)
        path = paths.views_daily / filename
        lines = ["---", f'date: "{day}"', f"sessions: {len(sessions)}", "---", "", f"# {day}", ""]
        for session in sorted(sessions, key=lambda item: item.get("recorded_at", "")):
            lines += [
                f"## {session['id']}",
                "",
                session.get("summary", "_No summary._") or "_No summary._",
                "",
                f"- source: `{session.get('source', '')}`",
                f"- workspace: `{session.get('workspace', '')}`",
                f"- device: `{session.get('device_id', '')}`",
                f"- entities: {', '.join(session.get('entities', [])) or 'none'}",
            ]
            notes = session.get("notes", [])
            if notes:
                lines += ["", "### Notes", ""]
                lines.extend(f"- {note}" for note in notes)
            lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")

    prune_markdown_dir(paths.views_entities, keep_entity_views)
    prune_markdown_dir(paths.views_daily, keep_daily_views)
    export_obsidian(paths, state, adjacency, by_day)


def export_obsidian(
    paths: VaultPaths,
    state: MaterializedState,
    adjacency: dict[str, list[Relation]],
    by_day: dict[str, list[dict]],
) -> None:
    keep_entity_notes: set[str] = set()
    for entity in state.entities.values():
        note_name = obsidian_note_name(entity.name)
        filename = f"{note_name}.md"
        keep_entity_notes.add(filename)
        path = paths.obsidian_entities / filename
        aliases = unique([entity.name] + entity.aliases)
        lines = [
            "---",
            "aliases:",
            *[f'  - "{alias}"' for alias in aliases],
            "tags:",
            '  - "mnemo/entity"',
            f'  - "mnemo/type/{entity.entity_type.lower()}"',
            f'entity_type: "{entity.entity_type}"',
            f'confidence: "{entity.confidence}"',
            f'first_seen: "{entity.first_seen}"',
            f'last_seen: "{entity.last_seen}"',
            f"session_count: {len(entity.session_ids)}",
            "---",
            "",
            f"# {entity.name}",
            "",
            entity.summary or "_No summary yet._",
            "",
        ]
        if entity.aliases:
            lines += ["## Aliases", ""]
            lines.extend(f"- {alias}" for alias in entity.aliases)
            lines.append("")
        if entity.urls:
            lines += ["## References", ""]
            lines.extend(f"- {url}" for url in entity.urls)
            lines.append("")
        if entity.paths:
            lines += ["## Local Paths", ""]
            lines.extend(f"- `{value}`" for value in entity.paths)
            lines.append("")

        related = sorted(adjacency.get(entity.name, []), key=lambda item: (-item.weight, item.target))
        if related:
            lines += ["## Relations", ""]
            for relation in related:
                other = relation.target if relation.source == entity.name else relation.source
                other_note = obsidian_note_name(other)
                summary = f" - {relation.summary}" if relation.summary else ""
                lines.append(
                    f"- `[{relation.relation_type}]` [[entities/{other_note}|{other}]]{summary}"
                )
            lines.append("")

        if entity.session_ids:
            lines += ["## Seen In Sessions", ""]
            for session_id in entity.session_ids:
                session = state.sessions.get(session_id)
                if not session:
                    lines.append(f"- `{session_id}`")
                    continue
                day = session.get("date", "")
                if day:
                    lines.append(f"- `{session_id}` in [[daily/{day}|{day}]]")
                else:
                    lines.append(f"- `{session_id}`")
            lines.append("")

        path.write_text("\n".join(lines), encoding="utf-8")

    keep_daily_notes: set[str] = set()
    for day, sessions in by_day.items():
        filename = f"{day}.md"
        keep_daily_notes.add(filename)
        path = paths.obsidian_daily / filename
        lines = [
            "---",
            f'date: "{day}"',
            f"sessions: {len(sessions)}",
            'tags:',
            '  - "mnemo/daily"',
            "---",
            "",
            f"# {day}",
            "",
        ]
        for session in sorted(sessions, key=lambda item: item.get("recorded_at", "")):
            lines += [
                f"## {session['id']}",
                "",
                session.get("summary", "_No summary._") or "_No summary._",
                "",
                f"- source: `{session.get('source', '')}`",
                f"- workspace: `{session.get('workspace', '')}`",
                f"- device: `{session.get('device_id', '')}`",
            ]
            entities = session.get("entities", [])
            if entities:
                entity_links = ", ".join(
                    f"[[entities/{obsidian_note_name(name)}|{name}]]" for name in entities
                )
                lines.append(f"- entities: {entity_links}")
            else:
                lines.append("- entities: none")
            notes = session.get("notes", [])
            if notes:
                lines += ["", "### Notes", ""]
                lines.extend(f"- {note}" for note in notes)
            lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")

    home = paths.obsidian / "Home.md"
    lines = [
        "---",
        'tags:',
        '  - "mnemo/home"',
        "---",
        "",
        "# Mnemo",
        "",
        "Open this folder as an Obsidian vault to explore the local memory graph.",
        "",
        "## Daily Notes",
        "",
    ]
    if by_day:
        for day in sorted(by_day, reverse=True):
            lines.append(f"- [[daily/{day}|{day}]]")
    else:
        lines.append("- _No daily notes yet._")
    lines += ["", "## Entities", ""]
    if state.entities:
        for entity in sorted(state.entities.values(), key=lambda item: item.name):
            lines.append(f"- [[entities/{obsidian_note_name(entity.name)}|{entity.name}]]")
    else:
        lines.append("- _No entities yet._")
    lines.append("")
    home.write_text("\n".join(lines), encoding="utf-8")
    prune_markdown_dir(paths.obsidian_entities, keep_entity_notes)
    prune_markdown_dir(paths.obsidian_daily, keep_daily_notes)


def load_materialized(paths: VaultPaths) -> dict:
    path = paths.state / "materialized.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
