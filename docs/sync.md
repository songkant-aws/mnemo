# Sync notes

## Short answer

Yes, this can sync across devices.

## Best option

Use the Mnemo vault itself inside a cloud-synced folder:

- iCloud Drive
- Dropbox
- OneDrive
- Google Drive desktop sync
- Syncthing

Example:

```bash
python3 -m mnemo.cli init "~/Library/Mobile Documents/com~apple~CloudDocs/mnemo-vault"
```

Why this is safer than the reference design:

- the canonical source is append-only JSONL
- files are segmented by date and device
- derived views can be rebuilt if they drift

## Good fallback

Keep the vault local for speed, and mirror it to a sync folder:

```bash
python3 -m mnemo.cli init ~/.mnemo/vault --mirror-dir "~/Dropbox/mnemo-vault"
python3 -m mnemo.cli sync mirror
```

This is a better fit when:

- the sync client is slow on large workspaces
- you want to control when sync happens
- you want local writes even while offline

## Conflict strategy

Current strategy:

- canonical events are append-only
- event-level dedup is based on semantic content fingerprints
- multiple devices should use distinct `device_id` values
- rebuild if projections look stale

## Health checks

Use:

```bash
python3 -m mnemo.cli sync health
```

It reports:

- local-only files
- mirror-only files
- divergent files
- local-only and mirror-only event fingerprints
- true duplicate fingerprints where the same semantic event appears under
  different event ids

If only derived files differ, the recommended action is usually to rebuild or
push again. If canonical event files diverge, inspect before running two-way
sync.

Next upgrades that would make this even stronger:

- per-view tombstone handling
- optional periodic compaction into snapshots
- per-device sync policies
