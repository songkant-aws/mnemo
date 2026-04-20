# Mnemo Feedback — review weak memory and apply corrections

## Review candidates

```bash
mnemo feedback
```

This surfaces:

- ambiguous entities
- isolated entities
- weak or underspecified relations
- recent feedback history

## Apply feedback

```bash
echo '{"operations":[{"action":"update_entity","name":"MNEMO","summary":"Better summary"}]}' | mnemo feedback --stdin
```

Supported operations:

- `update_entity`
- `delete_entity`
- `update_relation`
- `delete_relation`
