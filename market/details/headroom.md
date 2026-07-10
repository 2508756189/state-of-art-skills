# Headroom

Use this skill to preserve useful working memory while reducing context waste.

## Source

Inspired by Headroom: `https://github.com/chopratejas/headroom` (Apache-2.0).

This skill is a lightweight operating pattern, not a vendored copy of the upstream tool.

## Workflow

1. State the active objective in one sentence.
2. Split context into four buckets:
   - `facts`: verified current state
   - `decisions`: choices already made
   - `open`: blockers, unknowns, or user choices still needed
   - `evidence`: exact files, commands, commits, logs, URLs, or line references
3. Drop repeated logs, obsolete hypotheses, and low-value raw output after extracting evidence.
4. Prefer targeted reads over broad file loading.
5. When a task spans repos or machines, keep a short path map.
6. Track throughput and budget signals when they matter: slow upstreams, tokens/sec, repeated retries, oversized logs, or stalled builds. Keep the bottleneck as evidence, not raw noise.
7. Before a handoff, produce a compact continuation note with enough detail to resume without re-scanning everything.

## When To Use

- The conversation has many prior commands and partial findings.
- The agent is about to make risky edits based on old context.
- Multiple skill roots, repos, services, or configs are involved.
- The user says things like "继续", "接着来", "别重新扫", "总结一下当前状态", or "上下文太长".

## Output Shape

Keep the summary short:

```text
Objective:
Current state:
Decisions:
Open risks:
Next action:
Evidence:
```

Do not hide unresolved risk behind a tidy summary.
