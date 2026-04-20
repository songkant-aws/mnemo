# Mnemo Queue — inspect or consume queued session breadcrumbs

## Show pending queue items

```bash
mnemo queue status
```

## Consume them into replayable memory events

```bash
mnemo queue consume
```

Mnemo also auto-consumes queue items before `status`, `query`, `merge`, and
`feedback` unless `--no-queue` is passed.
