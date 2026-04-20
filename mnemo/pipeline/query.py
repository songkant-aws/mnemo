"""Local retrieval logic."""

from __future__ import annotations

import re
from collections import defaultdict, deque


STOP_WORDS = {
    "THE", "AND", "FOR", "WITH", "THIS", "THAT", "FROM", "WHAT", "WHEN",
    "WHERE", "WHY", "HOW", "DID", "WAS", "WERE", "ARE", "IS", "TO", "OF",
}


def tokenize(text: str) -> list[str]:
    tokens = [re.sub(r"[^A-Za-z0-9_]", "", token).upper() for token in text.split()]
    return [token for token in tokens if len(token) >= 3 and token not in STOP_WORDS]


def _score_haystack(tokens: list[str], haystack: str, exact_name: str = "") -> float:
    total = 0.0
    upper = haystack.upper()
    exact = exact_name.upper()
    for token in tokens:
        if token in exact:
            total += 3.0
        if token in upper:
            total += 1.0
    return total


def query(materialized: dict, question: str) -> dict:
    entities = materialized.get("entities", {})
    relations = materialized.get("relations", {})
    adjacency = materialized.get("adjacency", {})
    relation_summaries = materialized.get("relation_summaries", {})
    sessions = materialized.get("sessions", {})
    tokens = tokenize(question)

    scores: dict[str, float] = defaultdict(float)
    for name, entity in entities.items():
        haystack = " ".join(
            [
                name,
                entity.get("summary", ""),
                " ".join(entity.get("aliases", [])),
                " ".join(entity.get("tags", [])),
                " ".join(entity.get("paths", [])),
                " ".join(entity.get("urls", [])),
                " ".join(relation_summaries.get(name, [])),
            ]
        )
        scores[name] += _score_haystack(tokens, haystack, exact_name=name)

    matched = [name for name, _ in sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:8] if _ > 0]

    session_scores = []
    for session_id, session in sessions.items():
        haystack = " ".join(
            [
                session.get("summary", ""),
                session.get("workspace", ""),
                " ".join(session.get("entities", [])),
                " ".join(session.get("notes", [])),
            ]
        )
        score = _score_haystack(tokens, haystack, exact_name=session_id)
        if score > 0:
            session_scores.append((score, session_id, session))
    session_scores.sort(key=lambda item: (-item[0], item[1]))

    expanded: list[dict] = []
    seen = set(matched)
    queue = deque([(name, 0) for name in matched[:4]])
    while queue:
        name, depth = queue.popleft()
        if depth >= 2:
            continue
        for neighbor in adjacency.get(name, []):
            if neighbor in seen:
                continue
            seen.add(neighbor)
            expanded.append({"name": neighbor, "depth": depth + 1})
            queue.append((neighbor, depth + 1))

    relation_hits = []
    for relation in relations.values():
        score = 0.0
        if relation["source"] in matched or relation["target"] in matched:
            score += 2.0
        score += _score_haystack(tokens, " ".join([relation.get("summary", ""), relation.get("relation_type", "")]))
        if score <= 0:
            continue
        enriched = dict(relation)
        enriched["score"] = round(score, 2)
        relation_hits.append(enriched)
    relation_hits = sorted(relation_hits, key=lambda item: (-item["score"], -item["weight"], item["source"], item["target"]))[:12]

    contexts = []
    for name in matched:
        entity = entities[name]
        contexts.append(
            {
                "name": name,
                "entity_type": entity.get("entity_type", "CONCEPT"),
                "summary": entity.get("summary", ""),
                "related": adjacency.get(name, [])[:6],
                "paths": entity.get("paths", []),
                "urls": entity.get("urls", []),
                "aliases": entity.get("aliases", []),
            }
        )

    matched_sessions = []
    for score, session_id, session in session_scores[:8]:
        matched_sessions.append({
            "id": session_id,
            "score": round(score, 2),
            "summary": session.get("summary", ""),
            "workspace": session.get("workspace", ""),
            "entities": session.get("entities", []),
            "notes": session.get("notes", [])[:5],
            "recorded_at": session.get("recorded_at", ""),
        })

    return {
        "question": question,
        "tokens": tokens,
        "matched_entities": matched,
        "matched_sessions": matched_sessions,
        "contexts": contexts,
        "expanded_entities": expanded[:16],
        "relations": relation_hits,
    }
