# Mnemo — capture memory from the current session

Use Mnemo when this session produced reusable knowledge:

- a bug/fix
- a design decision
- a new subsystem
- a workflow or pattern worth remembering

## Steps

1. Extract structured memory from this conversation.

Use this JSON shape:

```json
{
  "session": {
    "id": "optional-stable-session-id",
    "date": "YYYY-MM-DD",
    "summary": "One paragraph summary",
    "workspace": "/absolute/path/to/workspace",
    "source": "claude-code"
  },
  "entities": [
    {
      "name": "MEMORY_NAME",
      "entity_type": "PROJECT|TOOL|CONCEPT|PERSON|ORGANIZATION",
      "description": "Detailed markdown description",
      "confidence": "EXTRACTED|INFERRED|AMBIGUOUS",
      "url": "https://canonical.example",
      "references": ["https://issue-or-doc"],
      "local_path": "/absolute/path"
    }
  ],
  "relations": [
    {
      "source": "MEMORY_A",
      "target": "MEMORY_B",
      "relation_type": "implements|depends_on|debugged_with|related_to",
      "description": "Short explanation",
      "weight": 0.8,
      "confidence": "EXTRACTED|INFERRED|AMBIGUOUS"
    }
  ]
}
```

2. Save it:

```bash
echo '<json>' | mnemo capture --stdin
```

3. Report the result briefly and mention the generated daily view path.
