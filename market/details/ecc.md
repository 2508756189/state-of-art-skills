# ECC

Use this skill when the user wants one workflow to work across multiple agent runtimes without assuming a single tool API.

## Source

Inspired by ECC: `https://github.com/affaan-m/ecc` (MIT).

This skill is an interoperability guide, not a vendored copy of the upstream framework.

## Portability Rules

- Separate intent from runtime-specific tool names.
- Keep frontmatter clear and concise.
- Mark runtime-specific assumptions explicitly:
  - Codex: `apply_patch`, developer tools, Codex memory, Codex Desktop paths
  - Claude: hooks/plugins, `.claude/skills`, Claude Desktop project JSONL
  - Generic CLI: `git`, `rg`, `python`, `node`, `docker`, `psql`
- Avoid hardcoding one user's absolute paths unless the skill is intentionally local.
- Put scripts in `scripts/` and call them by relative path from the skill directory.
- Prefer environment variables for hostnames, bastion details, database URLs, and tokens.

## Adaptation Workflow

1. Read the source skill and identify target runtime.
2. Classify it:
   - `codex-only`
   - `claude-only`
   - `portable`
   - `portable after rewrite`
3. Replace unavailable tool names with generic CLI steps or runtime-specific alternatives.
4. Remove secrets and machine-only cache files.
5. Validate frontmatter and duplicate `name:` values in the destination runtime.
6. Document the placement decision in the repo index.

## Placement Guidance

- Codex-only skills belong in `.codex/skills`.
- Claude-only skills belong in `.claude/skills`.
- Portable local skills can live in `.agents/skills` or a shared repo.
- Plugin bundles should stay as plugin repos, not be flattened into a skill folder.
