# Architecture

Mnemo is built around one core idea:

> Keep canonical memory as append-only events, and treat graph views as
> projections.

## Layers

1. Capture layer
   - Claude Code plugin or any agent emits structured JSON.
   - `mnemo capture --stdin` appends one event to the daily log.

2. Canonical storage
   - `events/YYYY-MM-DD/<device-id>.jsonl`
   - Safe for merge-based sync tools because files append over time instead of
     being rewritten wholesale.
   - Merge directives and feedback corrections are events too.

3. Materialization layer
   - Replays the event log into:
     - entity index
     - relation index
     - adjacency map
     - Markdown views
     - Obsidian-ready notes
     - duplicate-event report
     - feedback history

4. Retrieval layer
   - Local lexical match over entities, relation summaries, session summaries,
     and queue-derived notes.
   - Deterministic and easy to debug.

5. Sync layer
   - The vault can live inside a cloud folder.
   - Or the vault can be mirrored into one with `mnemo sync mirror`.
   - `mnemo sync health` checks both sides before a two-way sync.

## Why not a mutable graph database?

Single-file mutable stores are awkward for cross-device sync. If two laptops
rewrite the same file while offline, conflicts become painful.

An append-only event log is much friendlier:

- each device writes to its own file segment
- rebuilds are deterministic
- conflicts are reduced to duplicate events, which are easier to detect
- Markdown views can be regenerated
- Obsidian graph notes can be regenerated too

## Queue flow

When Claude Code stops, the plugin hook writes a breadcrumb into `queue/`.
Mnemo can then:

- auto-consume queued breadcrumbs before `status`, `query`, `merge`, and
  `feedback`
- or ingest them explicitly with `mnemo queue consume`

That gives you a durable fallback even if a session was not manually captured.
