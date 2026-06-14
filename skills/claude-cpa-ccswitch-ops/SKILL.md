---
name: claude-cpa-ccswitch-ops
description: Use when configuring, checking, or troubleshooting this Windows Claude Desktop or Claude Code setup with CC Switch, CPA reverse proxy, Anthropic-compatible model routing, Kiro or third-party model profiles, CoworkVMService workspace errors, or required development skills/plugins.
---

# Claude CPA / CC Switch Ops

Use this skill for this machine's Claude Desktop and Claude Code environment when model routing, reverse proxies, workspace VM startup, or required development skills/plugins are involved.

Core rule: treat CC Switch as the profile and compatibility layer, and CPA (`cli-proxy-api`) as the upstream API router. Do not paste or print tokens, API keys, proxy auth, or CPA account entries.

## Current Architecture

Expected local chain:

```text
Claude Code
  -> ~/.claude/settings.json
  -> ANTHROPIC_BASE_URL=http://127.0.0.1:8317
  -> CPA cli-proxy-api.exe

Claude Desktop / Claude-3p
  -> AppData/Local/Claude-3p/configLibrary applied profile "CC Switch"
  -> http://127.0.0.1:15721/claude-desktop
  -> CC Switch
  -> CPA 8317 or another selected upstream profile
```

Current important files:

- `C:\Users\王曙辉\.claude\settings.json`
- `C:\Users\王曙辉\AppData\Local\Claude-3p\configLibrary\_meta.json`
- `C:\Users\王曙辉\AppData\Local\Claude-3p\configLibrary\00000000-0000-4000-8000-000000157210.json`
- `C:\Users\王曙辉\AppData\Local\Claude-3p\claude_desktop_config.json`
- `E:\CPA\config.yaml`

Use UTF-8 reads for these files. If PowerShell output shows Chinese paths as mojibake, verify with `[System.IO.File]::ReadAllText(..., [System.Text.Encoding]::UTF8)` and codepoints before editing.

## Expected Configuration

Claude Code `settings.json` should have:

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://127.0.0.1:8317",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "claude-sonnet-4-6",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "claude-opus-4-6",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "claude-haiku-4-5-20251001",
    "ENABLE_TOOL_SEARCH": "true"
  }
}
```

`ANTHROPIC_AUTH_TOKEN` must exist, but never print it. It may be a placeholder-style local token accepted by the proxy.

Claude Desktop / Claude-3p CC Switch profile should be a gateway profile:

```text
inferenceProvider=gateway
inferenceGatewayBaseUrl=http://127.0.0.1:15721/claude-desktop
inferenceGatewayAuthScheme=bearer
coworkEgressAllowedHosts=*
```

Current observed model mapping:

```text
claude-haiku-4-5  -> claude-haiku-4-5-20251001
claude-opus-4-8   -> claude-opus-4-6
claude-sonnet-4-6 -> claude-sonnet-4-6
```

Do not confuse `name` with `labelOverride`. In Desktop profile JSON, `name` is the model id exposed to Claude Desktop, while `labelOverride` is the displayed or routed label. If strict consistency is required and the gateway supports it, prefer `claude-opus-4-6 -> claude-opus-4-6`.

## Third-Party Model Rule

For this setup, third-party models such as DeepSeek or GLM should be configured in CC Switch profiles, not directly in CPA's Claude route, unless a later test proves otherwise.

Reasoned analysis:

- CPA is useful as a local API router and credential/proxy hub.
- Claude Desktop expects a Claude/Anthropic-compatible Desktop gateway surface, model ids, streaming behavior, and tool/beta compatibility.
- CC Switch provides the Desktop-facing compatibility/profile layer at `/claude-desktop`.
- Directly putting non-Claude third-party models into CPA's Claude route has already been tested and did not work reliably in this environment.
- Likely failure modes are schema mismatch, streaming differences, tool-use/beta header incompatibility, model-name discovery mismatch, or unsupported Claude Desktop expectations.

Practical rule: use CPA for upstream access and CPA-native models; use CC Switch to present stable Claude model ids and route to CPA, Kiro, or third-party profiles.

## Kiro / Official Reverse Proxy

If switching to a Kiro or official reverse-proxy service:

1. Create or select a separate CC Switch profile.
2. Keep CPA and third-party profile credentials separate.
3. Point Claude Desktop to the CC Switch local gateway, not directly to the remote service unless intentionally testing.
4. Update Claude Code `settings.json` through CC Switch or a known-good profile rather than hand-editing live secrets.
5. Verify `/v1/models` before opening a real session.

Do not overwrite the working CPA profile without a backup.

## Quick Checks

Check service and proxy state:

```powershell
Get-NetTCPConnection -LocalPort 8317,15721 -ErrorAction SilentlyContinue |
  Select-Object LocalAddress,LocalPort,State,OwningProcess,
    @{Name='ProcessName';Expression={(Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue).ProcessName}}

Get-Service -Name CoworkVMService
```

Expected processes:

```text
8317  -> cli-proxy-api.exe from E:\CPA
15721 -> cc-switch.exe
CoworkVMService -> Running when Claude workspace/Cowork is needed
```

Check model endpoints without printing secrets:

```powershell
$settings = [System.IO.File]::ReadAllText("$env:USERPROFILE\.claude\settings.json", [System.Text.Encoding]::UTF8) | ConvertFrom-Json
$base = $settings.env.ANTHROPIC_BASE_URL.TrimEnd('/')
$token = $settings.env.ANTHROPIC_AUTH_TOKEN
Invoke-WebRequest -Uri "$base/v1/models" -Headers @{
  'x-api-key' = $token
  'anthropic-version' = '2023-06-01'
} -TimeoutSec 10 -UseBasicParsing
```

For Desktop profile:

```powershell
$cfg = [System.IO.File]::ReadAllText("$env:LOCALAPPDATA\Claude-3p\configLibrary\00000000-0000-4000-8000-000000157210.json", [System.Text.Encoding]::UTF8) | ConvertFrom-Json
$base = $cfg.inferenceGatewayBaseUrl.TrimEnd('/')
$key = $cfg.inferenceGatewayApiKey
Invoke-WebRequest -Uri "$base/v1/models" -Headers @{
  'Authorization' = "Bearer $key"
  'x-api-key' = $key
  'anthropic-version' = '2023-06-01'
} -TimeoutSec 10 -UseBasicParsing
```

Summarize status codes and model ids only. Do not echo key values.

## CoworkVMService

The error below is a workspace VM service problem, not a model reverse-proxy problem:

```text
Failed to start Claude's workspace
VM service not running. The service failed to start.
```

Check and start:

```powershell
Get-Service -Name CoworkVMService
Start-Service -Name CoworkVMService
```

If the service is running but Claude still shows the old error, restart Claude Desktop so it reconnects to `\\.\pipe\cowork-vm-service`.

Read detailed service logs:

```powershell
Get-Content -LiteralPath 'C:\ProgramData\Claude\Logs\cowork-service.log' -Tail 120
Get-Content -LiteralPath "$env:LOCALAPPDATA\Claude-3p\logs\cowork_vm_node.log" -Tail 120
```

## Required Skills

For this environment, keep these user skills installed in `C:\Users\王曙辉\.claude\skills`:

- `ai-read-fix`
- `production-ops`
- `postgresql-debug`
- `postgresql-report-reconciliation`
- `fz-flow`
- `fz-hlht-charging-ops`
- `fz-lot-onboarding`
- `systematic-debugging`
- `test-driven-development`
- `verification-before-completion`
- `dispatching-parallel-agents`
- `subagent-driven-development`
- `playwright`
- `playwright-interactive`
- `github`
- `build-mcp-server`
- `build-mcp-app`
- `build-mcpb`
- `cli-creator`

Before adding more skills, check for duplicate `name:` fields. Duplicate skill names can cause unstable skill selection.

## Useful Plugins

Useful official plugins already suited to this setup include:

- `github`
- `playwright`
- `code-review`
- `feature-dev`
- `pr-review-toolkit`
- `typescript-lsp`
- `pyright-lsp`
- `serena`
- `context7`
- `mcp-server-dev`
- `mcp-tunnels`
- `security-guidance`
- `session-report`
- `terraform`
- language LSP plugins such as `gopls-lsp`, `rust-analyzer-lsp`, `clangd-lsp`, `jdtls-lsp`, `csharp-lsp`, `php-lsp`, `ruby-lsp`, `lua-lsp`, `kotlin-lsp`, and `swift-lsp`

Plugins are registered in `.claude.json` under `pluginUsage`. The plugin source directories live under:

```text
C:\Users\王曙辉\.claude\plugins\marketplaces\claude-plugins-official
```

## Safe Edit Rules

- Back up `.claude.json`, `.claude\settings.json`, Desktop configLibrary entries, and CPA `config.yaml` before editing.
- Never print or persist plaintext API keys in summaries.
- Prefer CC Switch profile switching over direct manual edits.
- Use `Test-NetConnection` and `/v1/models` checks before blaming Claude.
- If `8317` and `15721` are healthy but workspace fails, debug `CoworkVMService`, not CPA.
- If Chinese paths look garbled in terminal output, verify bytes/codepoints before changing files.

