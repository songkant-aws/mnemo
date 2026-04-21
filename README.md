# Mnemo

Local-first memory for coding agents.

`mnemo` captures session knowledge as append-only events, rebuilds human-readable
views, exports Obsidian-ready notes, and keeps the canonical data layout friendly
to cloud-synced folders.

## Why this exists

The reference project proved the UX: save session knowledge into a local vault
and query it later. This rewrite keeps the same spirit, but changes the
architecture:

- Canonical data is an append-only event log, which is much safer for
  cross-device sync than a constantly-mutating graph file.
- Human-facing Markdown views are derived projections and can be rebuilt.
- Retrieval stays local and deterministic.
- Sync is treated as a storage concern, not mixed into capture/query logic.

## Design

```text
Claude Code / agent
  -> plugin command
  -> mnemo capture --stdin
  -> events/YYYY-MM-DD/<device>.jsonl   (canonical, sync-safe)
  -> rebuild projections
  -> views/entities/*.md
  -> views/daily/*.md
  -> obsidian/entities/*.md
  -> obsidian/daily/*.md
  -> state/materialized.json
```

## Commands

- `mnemo init [PATH]`
- `mnemo capture --stdin`
- `mnemo query --question "..."`
- `mnemo status`
- `mnemo rebuild`
- `mnemo auto [on|off|status]`
- `mnemo queue status`
- `mnemo queue consume`
- `mnemo merge`
- `mnemo feedback`
- `mnemo sync status`
- `mnemo sync health`
- `mnemo sync mirror`

## Vault layout

```text
~/.mnemo/
├── config.json
└── vault/
    ├── events/              # canonical append-only source of truth
    ├── views/               # derived Markdown projections
    ├── obsidian/            # Obsidian-ready notes for Graph View
    ├── state/               # rebuildable indexes and manifests
    ├── queue/               # local capture breadcrumbs
    └── sync/                # sync metadata
```

## Cross-device sync

Two practical options work well:

1. Put the whole vault inside a cloud-synced folder such as iCloud Drive,
   Dropbox, OneDrive, Google Drive, or Syncthing.
2. Keep the vault local and configure `sync.mirror_dir`, then run
   `mnemo sync mirror`, `mnemo sync health`, or a scheduled sync job.

The canonical store is append-only JSONL segmented by date and device, so cloud
merges are much less risky than a single mutable database file.

More details: [docs/sync.md](docs/sync.md)

## Obsidian Graph View

After any `mnemo rebuild` or `mnemo capture`, Mnemo exports an Obsidian-friendly
note set under `vault/obsidian/`.

Open this folder as your Obsidian vault:

```bash
~/.mnemo/vault/obsidian
```

The export includes:

- `entities/*.md` with wikilinks between related entities
- `daily/*.md` with wikilinks back to entity notes
- `Home.md` as a simple landing page

That makes Obsidian Graph View usable without treating the raw event log or
state files as notes.

## Claude Code plugin

The repository includes a Claude Code plugin under [`plugin/`](plugin/) with
commands for capture, query, status, rebuild, merge, feedback, queue review,
and sync inspection.

Install it from source with:

```bash
claude plugin marketplace add /Users/songkant/workspace/mnemo
claude plugin install mnemo
```

Suggested setup after install:

```bash
python3 -m mnemo.cli init ~/.mnemo/vault
python3 -m mnemo.cli auto on
```

## Codex one-click install

To install the Codex-local plugin package in one command:

```bash
zsh /Users/songkant/workspace/mnemo/install-codex-plugin.sh
```

This will:

- copy the Codex plugin bundle into `~/plugins/mnemo`
- update `~/.agents/plugins/marketplace.json`
- initialize `~/.mnemo/config.json` if Mnemo has never been configured

After that, restart or refresh Codex so it reloads local plugins.

## Development

This project uses only the Python standard library and currently runs on Python
3.9+.

```bash
python3 -m mnemo.cli init
python3 -m mnemo.cli status
```
