# Mnemo Merge — suggest or apply entity merges

## Review likely duplicates

```bash
mnemo merge
```

Look at:

- `score`
- `shared_tokens`
- both summaries

## Apply a merge

```bash
echo '{"merges":[{"canonical":"KEEP_THIS","aliases":["REMOVE_THIS"]}]}' | mnemo merge --stdin
```

Merge directives are stored as replayable events, so they survive rebuilds and
sync.
