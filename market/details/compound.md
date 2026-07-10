# Compound

Use this skill for orchestration-heavy engineering tasks where quality depends on sequencing and feedback loops.

## Source

Inspired by Every's Compound Engineering Plugin: `https://github.com/everyinc/compound-engineering-plugin` (MIT).

This skill captures the workflow pattern only. Do not assume the upstream plugin is installed.

## Workflow

1. Define the deliverable and non-goals.
2. Split work into independent tracks only when they can be validated separately.
3. Assign each track a concrete output:
   - code change
   - test result
   - research note
   - risk list
   - review finding
4. Integrate outputs into one implementation path.
5. Before review, simplify the implementation: remove stale scaffolding, collapse avoidable indirection, and make the change easy to inspect.
6. Treat review output as a report of findings and evidence. Apply fixes deliberately after reconciling them with the current code, tests, and user goal.
7. Run verification before claiming completion.
8. Leave a concise handoff with files changed, tests run, remaining risk, and next step.

## Good Use Cases

- Larger repo changes touching backend, frontend, and tests.
- Architecture choices with competing approaches.
- Multi-service debugging where logs, DB, code, and config all matter.
- Preparing a PR with review, CI, and docs updates.

## Avoid

- Spawning parallel work when a single file read would answer the question.
- Using orchestration language as a substitute for verification.
- Creating unnecessary plans for small, obvious edits.
