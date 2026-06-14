---
name: cli-db-code-workflow
description: Standard CLI workflow for Codex in a Windows workspace. Use when the user asks how Codex connects to PostgreSQL from the CLI with user-provided connection details, inspects databases, reads project code, searches files, edits files safely, validates changes, or wants these operational habits documented as a reusable skill. This skill intentionally excludes git workflows.
---

# CLI DB Code Workflow

Use this skill as the operating guide for database access, code inspection, and safe file editing in the current Windows workspace.

## First Moves

1. Work from the user's current workspace unless a task gives a different path.
2. Prefer PowerShell-compatible commands because the active shell is usually `powershell`.
3. Read before editing. Build context with fast search, targeted file reads, and DB schema discovery.
4. Never hardcode database host, port, database name, username, or password in the skill. Ask the user to provide connection details when live DB access is needed.
5. Use `apply_patch` for manual file edits. Do not create or edit files with `cat`, `Set-Content`, shell redirection, or ad hoc Python when a simple patch is enough.
6. Do not perform or document git operations in this skill.

## Reference Map

- `references/db-cli.md`: PostgreSQL CLI connection patterns, PowerShell quoting, schema discovery, and safe production-query habits.
- `references/code-file-tools.md`: preferred tools for searching, reading, editing, validating, and reporting code changes.

## CLI Database Access

Use `psql` for PostgreSQL work whenever possible. Require the user to provide `host`, `port`, `database`, `username`, and `password` before attempting a live connection. In PowerShell, pass passwords through `PGPASSWORD` for one command, then clear it:

```powershell
$env:PGPASSWORD = '<password-from-user>'
psql -h <host> -p <port> -U <user> -d <database> -c "select current_database(), current_schema();"
Remove-Item Env:\PGPASSWORD
```

If the user has not provided complete connection details, ask for the missing values instead of guessing or reusing project-specific defaults.

## Code Reading Tools

Prefer fast, narrow inspection:

- Use `rg --files` to list files.
- Use `rg -n "pattern" path` to search code.
- Use `Get-Content -Path file` for whole small files.
- Use `Select-String -Path file -Pattern "pattern"` for PowerShell-native targeted searches.
- Use `Get-ChildItem` for directory discovery.
- Use parallel tool calls when reads are independent.

## File Editing Rules

- Use `apply_patch` for manual edits.
- Keep patches small and focused.
- Use formatting or generation commands only after patching when they are normal project tools.
- Validate with targeted tests, lint, or command-line checks when feasible.

## Reporting Back

When closing a task:

- Mention the files changed with absolute links if useful.
- State the verification command or DB query that was run.
- State clearly if live DB access, tests, or deployment checks were not run.
- Summarize the behavior change, not just the file list.
