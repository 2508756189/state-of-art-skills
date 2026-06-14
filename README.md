# State-of-Art Skills

Curated external-inspired and imported skills for Codex, Claude, and portable coding-agent workflows.

This repository intentionally separates:

- external-inspired adaptation skills
- imported high-signal skills from public skill repositories
- runtime placement guidance

Private by default while curation and runtime adaptation are still evolving.

## Layout

```text
skills/
  <skill-name>/
    SKILL.md
    agents/openai.yaml      # optional
    scripts/                # optional
    references/             # optional
```

## Runtime Placement

- Codex-only skills: install to `.codex/skills`.
- Claude-only skills: install to `.claude/skills`.
- Portable skills: install to `.agents/skills` and optionally mirror to Claude after review.

Do not blindly sync the whole repository into every runtime. Classify each skill first.

## External-Inspired Skills

These skills are lightweight local adaptations and source-attribution wrappers. They do not vendor upstream repositories.

- `markitdown`: inspired by `https://github.com/microsoft/markitdown`
- `headroom`: inspired by `https://github.com/chopratejas/headroom`
- `taste-skill`: inspired by `https://github.com/leonxlnx/taste-skill`
- `supermemory`: inspired by `https://github.com/supermemoryai/supermemory` and `https://github.com/supermemoryai/claude-supermemory`
- `compound`: inspired by `https://github.com/everyinc/compound-engineering-plugin`
- `ecc`: inspired by `https://github.com/affaan-m/ecc`

## Imported Skill Sources

Selected high-signal skills are imported and namespaced from `https://github.com/anbeime/skill` after review, not blindly mirrored:

- `anbeime-agent-team`
- `anbeime-multi-agent-meeting`
- `anbeime-content-research-writer`
- `anbeime-product-manager-toolkit`
- `anbeime-frontend-design`
- `anbeime-web-design-analyzer`

These use the `anbeime-` prefix to avoid collisions with local skills and plugin-provided skills.

## Safety

Before pushing:

- check for secrets, tokens, cookies, private account exports, and `.env` files
- validate every `SKILL.md` frontmatter
- check duplicate `name:` values
- keep generated caches and local backups out of git
