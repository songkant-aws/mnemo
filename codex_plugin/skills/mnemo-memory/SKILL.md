---
name: mnemo-memory
description: Query, capture, review, and sync the local Mnemo memory vault from Codex.
---

# Mnemo Memory

Use this skill when the user asks to:

- recall prior local work or previous sessions
- save current work into long-term local memory
- inspect queue, merge candidates, or feedback candidates
- check multi-device sync health

## Command wrapper

Use the local wrapper script:

```bash
~/plugins/mnemo/scripts/mnemo <command> ...
```

## Common commands

### Query memory

```bash
~/plugins/mnemo/scripts/mnemo query --question "stderr bug fix"
```

### Show status

```bash
~/plugins/mnemo/scripts/mnemo status
```

### Consume queued session breadcrumbs

```bash
~/plugins/mnemo/scripts/mnemo queue status
~/plugins/mnemo/scripts/mnemo queue consume
```

### Review duplicate-like entities

```bash
~/plugins/mnemo/scripts/mnemo merge
```

### Review weak memory and corrections

```bash
~/plugins/mnemo/scripts/mnemo feedback
```

### Check multi-device sync health

```bash
~/plugins/mnemo/scripts/mnemo sync status
~/plugins/mnemo/scripts/mnemo sync health
```

## Working style

- Query first when prior context may help.
- Capture at the end of meaningful work.
- Prefer `sync health` before advising on cross-device sync issues.
- Prefer merge and feedback events over hand-editing derived files.
