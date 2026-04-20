---
name: query-local-memory
description: Search the local Mnemo vault for prior sessions, entities, and relations before answering coding or project-context questions.
---

# Query Local Memory

Use this skill when the user asks things like:

- "have we done this before?"
- "what did I do last time?"
- "look up my local memory"
- "search my notes about this project"

## Commands

```bash
~/plugins/mnemo/scripts/mnemo query --question "<question>"
~/plugins/mnemo/scripts/mnemo status
~/plugins/mnemo/scripts/mnemo activity recent
```

## Guidance

- Query before making assumptions about prior work.
- Use `matched_sessions` to recover prior threads and reasoning.
- Use `contexts` and `relations` to summarize durable entities and links.
- If the result is thin, try a second query with sharper nouns.
