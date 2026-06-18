# TokenPort Skill Market

Curated skill packs for TokenPort, Codex, Claude Code, and portable coding-agent workflows.

This repository is now a lightweight Skill Market:

- `skills/` stores reviewed skill source directories.
- `market/categories.json` classifies skills for product display.
- `market/index.json` is the generated registry consumed by TokenPort/Sub2API.
- `dist/skills/*.zip` contains installable skill archives with SHA256 checksums.

## Registry

Consumers fetch the registry from jsDelivr (CORS-enabled, globally cached, reachable from mainland China):

```text
https://cdn.jsdelivr.net/gh/2508756189/state-of-art-skills@main/market/index.json
```

`raw.githubusercontent.com` is a fallback for environments where jsDelivr is blocked.

Registry schema:

```text
market/schema.v1.json
```

Each registry item contains:

- `id`, `name`, `description`
- `category`, `tags`, `runtime`
- `installTargets` for Codex, Claude, and portable runtimes
- `version`, `license`, `source`, `riskLevel`
- `archive.path`, `archive.sha256`, `archive.size`

## Install Targets

Use the registry-provided install target for the runtime you are configuring:

| Runtime | Default target |
| --- | --- |
| Codex | `~/.codex/skills/<skill-id>` |
| Claude Code | `~/.claude/skills/<skill-id>` |
| Portable/shared | `~/.agents/skills/<skill-id>` |

TokenPort should generate a copyable install command rather than writing local files from the browser.

## Build And Validate

```powershell
python scripts\test_build_market.py
python scripts\build_market.py
```

The build script:

- parses every `skills/*/SKILL.md` frontmatter
- rejects duplicate skill names
- scans for secret-like values
- writes `market/index.json`
- creates `dist/skills/*.zip`
- records SHA256 and archive size in the registry

CI runs the same checks in `.github/workflows/validate-market.yml`.

## Skill Curation

Current categories:

- `engineering`: code development, review, interoperability, and engineering workflows
- `product`: research, PRD, prioritization, and product strategy
- `design`: frontend design, design-system extraction, and product taste
- `knowledge`: document conversion, presentation generation, context, memory, and knowledge capture
- `workflow`: multi-agent collaboration and meeting/decision workflows

Do not blindly sync the whole repository into every runtime. Classify each skill first and install only the selected packages.

## Safety

Before publishing:

- run the market build script
- check generated registry and archive checksums
- verify source attribution and license notes
- keep account exports, cookies, `.env`, and private keys out of skills
- mark skills with external services, code execution, or filesystem assumptions as `medium` or `high` risk
