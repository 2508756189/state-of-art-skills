---
name: codex-config-sync
description: Use when the user asks Codex to inspect, compare, back up, upload, commit, push, or synchronize local Codex configuration, skills, plugins, memories, automations, TOML settings, OpenAI tool configuration, local proxy/provider health, compact-summary failures, plugin visibility, or dependency reinstall state. Especially useful for C:\Users\Administrator\.codex work where local and remote skill/config state must end aligned despite encoding issues, git transport failures, or unclear TOML/plugin locations.
---

# Codex Config Sync

Use this skill for repeatable local Codex environment maintenance. The goal is to make local and remote configuration end in the same verified state, not just to edit one file.

## Workflow

1. Inspect the live Codex home first.
   - Default path on this machine: `C:\Users\Administrator\.codex` unless `$env:CODEX_HOME` is set.
   - Check `config.toml`, `skills/`, `plugins/`, `automations/`, `memories/`, and relevant git remotes before speculating.
2. Preserve existing assets.
   - Prefer updating an existing skill, plugin, automation, or config entry over creating a duplicate.
   - Back up changed files when the change is broad or affects production-facing workflows.
3. Handle Windows encoding deliberately.
   - Use UTF-8-safe reads and writes for Chinese paths and TOML/Markdown content.
   - If PowerShell output is mojibake, verify with Python explicit UTF-8 before changing source files.
4. Validate the resulting state.
   - For skills, verify `SKILL.md` frontmatter has only `name` and `description` and that the folder name is stable.
   - For config, parse or inspect the relevant TOML/JSON rather than trusting visual output.
   - For git sync, compare local branch, remote branch, status, and last commit after push.
5. Keep pushing through transient sync issues.
   - If a push fails due to transport/network, retry safely after checking branch and remote.
   - Do not change production branches or unknown remotes without explicit user direction.

## Codex Proxy And Compact Health

Use this section when the symptoms are `git fetch` failures for Codex dependencies, plugins disappearing, empty compact summaries, remote compact errors, or custom provider timeouts.

1. Split Git transport from general network reachability.
   - Test the actual Git/libcurl path with `git ls-remote https://github.com/openai/skills.git HEAD`.
   - If a local proxy is required, verify the proxy path directly, then inspect global Git proxy keys.
2. Inspect active Codex config and provider health.
   - Parse `C:\Users\Administrator\.codex\config.toml`.
   - Run `codex doctor` when available.
   - If `base_url` points to a custom provider or local proxy, treat reachability as drift-prone and verify before editing thread files.
3. Diagnose compact failures from rollout JSONL evidence.
   - Empty compact summaries show up as `type: "compacted"` with `payload.message = ""`.
   - If multiple threads have empty compact payloads, treat it as systemic provider/proxy/request-shape trouble, not one corrupted conversation.
   - Errors mentioning `tools.defer_loading` and `tools.tool_search` usually point to a proxy/request-translation mismatch before they point to a workspace bug.
4. Make minimal local config changes first.
   - Back up `config.toml` before edits.
   - Prefer small reversible changes such as restoring response storage over bulk state rewrites.
   - If the desktop app is open, expect `.codex-global-state.json` and install flags to be rewritten; close Codex Desktop before durable state edits.
5. For CLI Proxy API maintenance:
   - Distinguish management-panel updates from binary/service updates.
   - Verify the running executable or bundle path before replacing files.
   - Recheck the management route, commonly `http://localhost:8317/management.html`, after a panel update.

## Common Checks

```powershell
$root = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { "$HOME\.codex" }
Get-ChildItem -Force $root
Get-ChildItem -Directory "$root\skills"
Get-Content -Raw "$root\config.toml"
git ls-remote https://github.com/openai/skills.git HEAD
codex doctor
```

## Output Expectations

- State what changed, what was already covered, and what remains unsynced.
- Include exact paths for edited skills/config files.
- If asked to upload, report the branch, remote, commit hash, and verification command result.
- If evidence is insufficient, say what source is missing instead of creating speculative config.
