# Supermemory

Use this skill when the task is about durable memory: saving what matters, finding prior context, or deciding what should not be stored.

## Source

Inspired by Supermemory and Claude Supermemory:

- `https://github.com/supermemoryai/supermemory` (MIT)
- `https://github.com/supermemoryai/claude-supermemory` (MIT)

This skill does not assume the service is installed. Treat external memory APIs as optional.

## Capture Rules

Save only stable, reusable facts:

- repo locations and workflow patterns
- validated commands
- service topology without secrets
- decisions and their rationale
- recurring error signatures and fixes
- safe schema or report-shape facts

Never save:

- API keys, tokens, cookies, private account entries
- one-time auth codes
- full customer data or sensitive chat exports
- live credentials from config files
- speculative guesses not marked as guesses

## Retrieval Workflow

1. Clarify what memory is needed: repo, service, date, feature, incident, or workflow.
2. Search local memory first if available.
3. Search external memory only if configured and appropriate.
4. Distinguish memory-derived facts from currently verified facts.
5. Re-verify drift-prone facts before acting on production, credentials, schedules, or live services.

## Capture Output

When saving memory, keep it short:

```text
Context:
Reusable fact:
Evidence:
Do not store:
```
