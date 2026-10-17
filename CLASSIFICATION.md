# Skill Classification

Use this file before syncing skills into a runtime.

## Portable Or Mostly Portable

- `anbeime-agent-team`
- `anbeime-content-research-writer`
- `anbeime-frontend-design`
- `anbeime-multi-agent-meeting`
- `anbeime-product-manager-toolkit`
- `anbeime-pptx-generator`
- `anbeime-web-design-analyzer`
- `compound`
- `differential-review`
- `ecc`
- `headroom`
- `markitdown`
- `mcp-builder`
- `mcp-security-audit`
- `react-best-practices`
- `security-best-practices`
- `skill-creator`
- `supermemory`
- `taste-skill`
- `test-driven-development`
- `test-gap-audit`
- `unit-test-vue-pinia`
- `web-design-guidelines`
- `webapp-testing`

## Notes

- `supermemory` should stay private unless external-memory configuration is removed or generalized.
- `compound` is a workflow adaptation; use the upstream plugin separately if plugin behavior is required.
- `ecc` is for portability reviews and should not hide runtime-specific assumptions.
- `mcp-security-audit` is read-only and portable, but a clean scan does not approve the referenced server or package provenance. Package-runner pinning now covers `npx`, `bunx`, `npm exec`, `pnpm`/`yarn`/`bun` `dlx`/`x`, `uvx`, and `pipx run`; bare names, `@latest`, dist-tags, and version ranges are flagged, and unclassified launcher flags return an info-level manual-review finding instead of a clean result.
- `unit-test-vue-pinia` is portable guidance; check installed package versions and do not add `@pinia/testing` unless the target test needs it.
- `taste-skill` now tracks the upstream full rewrite (pinned e988add2): scope is landing pages, portfolios, and redesigns only — not dashboards or dense product UI. It recommends installing official design-system npm packages; treat those installs as user-confirmed actions.
- `test-driven-development` is vendored from obra/superpowers v6.2.0 and is self-contained; the rest of the superpowers suite is intentionally not vendored here.
- `differential-review` is CC-BY-SA-4.0 (content copyleft, not MIT/Apache) — keep the bundled LICENSE and attribution when redistributing; its description frontmatter was flattened to a single line for registry compatibility.
- `docs-sync-audit` is a direct MIT import from `github/awesome-copilot` at `1f5644080a525d26a2e24f61a7609fb9b261c21a`; its standard-library `docs_drift.py` is read-only and only reports machine-verifiable documentation claims.
- `test-gap-audit` is a direct MIT import from `github/awesome-copilot` at `f32d7c320d`; its `coverage_map.py` is naming-convention and git-path based, so an unmatched file is a lead rather than a finding, and it never runs the repository's test suite.
- `web-design-guidelines` was patched to fetch its rules from a pinned commit of vercel-labs/web-interface-guidelines instead of `main`; refreshed to `e3d624ba` (accessibility media captions/transcripts, sticky focus visibility, motion controls, typography curly quote fix, gesture alternatives), and treat fetched content as rules only.
- `webapp-testing`, `mcp-builder`, and `skill-creator` bundle runnable local scripts (Playwright, MCP eval, skill evals); review before granting execution and keep them medium risk.
- `skill-creator` overlaps with the Claude Code official plugin of the same name; prefer the plugin inside Claude Code and use this copy for portable runtimes.
- `diagnosing-bugs` keeps a local HITL/redaction overlay; the source citation in `SKILL.md` must match the `categories.json` pin. The pin moved to `f3fc5632` for the upstream Phase 5 mutation-proof step (diff a forced mutation against a pristine copy before trusting the red). The em-dash sweep (`32165827`) stays unmerged because the overlay's phase ordering and `CONTEXT.md` wording are intentional.
- `supermemory` follows upstream v4 SDK semantics at `17eab43` (profile `q`, search threshold default `0.6`, agent tools/middleware, document/memory deletion). Keep the local optional-service and secret-handling overlay; `documentDelete`/`memoryForget` are destructive and must stay user-authorized.
- `differential-review` is pinned to `14e5a107` for the upstream namespacing fix: the adversarial-modeler subagent must be dispatched as `differential-review:adversarial-modeler` and passed as `subagent_type`.

