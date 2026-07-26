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
- `ecc`
- `headroom`
- `markitdown`
- `mcp-security-audit`
- `supermemory`
- `taste-skill`
- `unit-test-vue-pinia`

## Notes

- `supermemory` should stay private unless external-memory configuration is removed or generalized.
- `compound` is a workflow adaptation; use the upstream plugin separately if plugin behavior is required.
- `ecc` is for portability reviews and should not hide runtime-specific assumptions.
- `mcp-security-audit` is read-only and portable, but a clean scan does not approve the referenced server or package provenance.
- `unit-test-vue-pinia` is portable guidance; check installed package versions and do not add `@pinia/testing` unless the target test needs it.
- `taste-skill` now tracks the upstream full rewrite (pinned e988add2): scope is landing pages, portfolios, and redesigns only — not dashboards or dense product UI. It recommends installing official design-system npm packages; treat those installs as user-confirmed actions.
