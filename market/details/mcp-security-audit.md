# MCP Security Audit

Use this skill for a read-only security review of MCP configuration before a server is enabled, promoted, or shared.

## Source And Curation

Inspired by GitHub's `github/awesome-copilot` skill `skills/mcp-security-audit` at commit `e95bd8c4ba65454121f86a7ad0d3ed17ab0bcf37` under the MIT license.

The market adaptation replaces illustrative snippets with one deterministic Python script, adds Codex TOML and Windows launcher handling, implements optional approved-server checks, redacts evidence, and documents limits. It does not copy or execute an MCP server.

## Workflow

1. Identify the configuration file and runtime. Supported shapes are:
   - JSON with `mcpServers`, `mcp_servers`, or `mcp.servers`.
   - TOML with `[mcp_servers.<name>]`, including Codex `config.toml`.
2. Run the bundled scanner:

```powershell
python scripts\audit_mcp_config.py C:\path\to\config.toml
```

3. When governance has an explicit allowlist, add one or more approved names:

```powershell
python scripts\audit_mcp_config.py .mcp.json --approved filesystem --approved github
```

4. Use `--json` for machine-readable output. The script reports locations and finding classes without printing credential values.
5. Review each finding against the actual launcher semantics. Direct process arguments are not shell code unless the configured command invokes a shell.
6. Verify the referenced package, executable, repository, release, and license separately before promotion. A clean configuration scan is not a supply-chain approval.

## Checks

- Hardcoded secrets, bearer tokens, private keys, and credentials embedded in URLs.
- Shell launchers such as `cmd /c`, PowerShell `-Command`, or `sh -c`.
- Unpinned packages launched through `npx`, `pnpm dlx`, `uvx`, or `pipx run`.
- Plain HTTP remote endpoints except loopback hosts.
- Servers missing from an explicitly supplied approved-name list.
- External hosts and environment variables that must exist at runtime.

## Risk And Runtime Limits

- The script is read-only: it does not edit configuration, execute launch commands, resolve packages, or make network requests.
- It supports Python 3.11+ because TOML parsing uses the standard-library `tomllib` module.
- It cannot prove that a referenced binary, npm/Python package, remote MCP endpoint, or environment variable is trustworthy.
- It cannot see credentials injected later by a parent process, shell profile, secret manager, or runtime plugin.
- Treat findings as review evidence, not automatic authorization to remove or enable a server.
- Never paste live secret values into reports, tests, issue bodies, or chat output.
## Minimum Realistic Smoke Test

Before promotion, run the scanner against:

- One safe pinned local server using environment-variable references.
- One intentionally unsafe sample containing a shell launcher, unpinned package, or hardcoded placeholder credential.
- At least one real local Codex or Claude MCP configuration in read-only mode, confirming that output remains redacted.
