---
name: refresh-memory-graph
description: Rebuild the local Mnemo vault into fresh Obsidian graph notes, then optionally open the Obsidian vault for graph exploration.
---

# Refresh Memory Graph

Use this skill when the user asks to:

- rebuild Mnemo memory into graph-ready notes
- refresh the Obsidian graph export
- reopen the Mnemo graph after new captures, merges, or feedback

## Workflow

1. Rebuild the vault:

```bash
~/plugins/mnemo/scripts/mnemo rebuild
```

2. Resolve the Obsidian export directory.

- Read `~/.mnemo/config.json` and use `vault_dir` when present.
- Otherwise assume the default vault root is `~/.mnemo/vault`.
- The Obsidian-ready vault is `<vault_dir>/obsidian`.

3. Tell the user the exact Obsidian vault path.

4. If the user wants it opened and the machine is macOS, open it:

```bash
open -a Obsidian "<vault_dir>/obsidian"
```

## Guidance

- Prefer this skill after meaningful capture, merge, or feedback work.
- Treat `obsidian/` as generated output that rebuild may overwrite.
- If rebuild succeeds but the graph looks stale, make sure Obsidian opened the `obsidian/` folder rather than the raw vault root.
