---
name: sync-memory-vault
description: Inspect sync health and coordinate local-to-cloud or cloud-to-local Mnemo vault synchronization.
---

# Sync Memory Vault

Use this skill when the user asks about:

- cross-device memory reuse
- cloud sync status
- local vs mirror drift
- safe push/pull behavior

## Commands

```bash
~/plugins/mnemo/scripts/mnemo sync status
~/plugins/mnemo/scripts/mnemo sync health
~/plugins/mnemo/scripts/mnemo sync mirror --direction push
~/plugins/mnemo/scripts/mnemo sync mirror --direction pull
```

## Guidance

- Run `sync health` before recommending two-way sync.
- If only derived files differ, rebuild or push again.
- If event files diverge, inspect before forcing both directions.
- Remind the user that distinct `device_id` values are important.
