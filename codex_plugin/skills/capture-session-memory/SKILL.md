---
name: capture-session-memory
description: Save the current Codex work into the local Mnemo vault as replayable memory events.
---

# Capture Session Memory

Use this skill near the end of meaningful work when the session produced:

- a bug fix
- a design decision
- a new subsystem
- a durable workflow insight

## Workflow

1. Check recent activity:

```bash
~/plugins/mnemo/scripts/mnemo activity recent
```

2. Build structured JSON for the current session.

3. Save it:

```bash
echo '<json>' | ~/plugins/mnemo/scripts/mnemo capture --stdin
```

## Guidance

- Prefer a few high-signal entities over many weak ones.
- Focus on bugs, fixes, decisions, and reusable context.
- Mention local paths for projects or concrete files when they matter.
