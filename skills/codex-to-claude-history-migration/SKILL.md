---
name: codex-to-claude-history-migration
description: Use when migrating Codex Desktop conversation history into Claude or Claude-3p local history on Windows, repairing imported Claude JSONL transcripts, preserving current thread titles, fixing Claude custom groups, removing Codex-only internal markers, and handling Chinese path or group-name mojibake in Claude Local Storage.
---

# Codex To Claude History Migration

Use this skill when the user wants Codex conversations to appear in Claude as readable, searchable local history. The priority is stable display and search, then faithful content. Do not try to make Codex tool calls replay as native Claude tool calls.

Bundled scripts live in `scripts/`:

- `codex_to_claude_history_import.py`: reads Codex `state_5.sqlite` + rollout JSONL and writes Claude project JSONL and Claude-3p session metadata.
- `polish_claude_import_history.py`: cleans imported transcripts, updates titles, repairs metadata, and validates residual Codex markers.
- `repair_claude_project_groups.js`: writes Claude-3p custom groups into Chromium LevelDB with mojibake-safe JSON escaping.

## Safety Rules

1. Close Claude and Claude-3p before writing `.claude`, Claude-3p session metadata, or Local Storage.
   - Verify with `Get-Process | Where-Object { $_.ProcessName -match 'Claude|claude' }`.
   - Stop it before edits if the user expects repair now.
2. Back up before every write:
   - `C:\Users\Administrator\.claude\projects`
   - `C:\Users\Administrator\.claude.json`
   - `C:\Users\Administrator\AppData\Local\Claude-3p\Local Storage\leveldb`
3. Treat Codex history as read-only. Read from `C:\Users\Administrator\.codex\state_5.sqlite` and rollout JSONL only.
4. Preserve user-renamed titles. Do not add project prefixes to thread names unless the user explicitly asks.
5. On Windows, never trust mojibake-looking terminal output alone. Verify JSON/SQLite/LevelDB with explicit UTF-8 readers.

## Standard Workflow

1. Create a scratch working directory.

```powershell
$work = "$HOME\Documents\Codex\codex-to-claude-history-migration"
New-Item -ItemType Directory -Force -Path $work | Out-Null
Copy-Item "$HOME\.codex\skills\codex-to-claude-history-migration\scripts\*" $work -Force
Set-Location $work
```

2. Configure target projects in `codex_to_claude_history_import.py`.
   - Edit `TARGETS` only.
   - Use `\uXXXX` escapes for Chinese literals if PowerShell or the editor has encoding drift.
   - Set `label` to the Claude project/custom group display name.
   - Set `slug` to an existing Claude project directory when one already exists.

3. Dry run candidate threads.

```powershell
python .\codex_to_claude_history_import.py --dry-run
```

Confirm:

- Candidate count matches the intended migration scope.
- Every `rollout_path` exists.
- Destination Claude project directories are correct.
- Active vs archived counts match the user's expectation.

4. Import.

For a cautious run:

```powershell
python .\codex_to_claude_history_import.py --canary
python .\codex_to_claude_history_import.py --validate
python .\codex_to_claude_history_import.py --validate-desktop-sessions
```

For the full run:

```powershell
python .\codex_to_claude_history_import.py --full
python .\codex_to_claude_history_import.py --desktop-sessions
```

5. Preserve or override titles.
   - If the user has screenshots or current names, create `claude_import_title_overrides.json` in the scratch directory.
   - Keys are imported Claude `session_id` values, not Codex thread ids.
   - Values should be exact desired titles, with no generated project prefix.
   - Use `ensure_ascii=True` JSON when writing Chinese title overrides to avoid PowerShell mojibake.

6. Polish transcripts and metadata.

```powershell
python .\polish_claude_import_history.py
```

The polish script should:

- Remove Codex-only wrappers such as `<environment_context>`, `<turn_aborted>`, `<codex_internal_context>`, and `<oai-mem-citation>`.
- Remove Codex desktop directives such as `::git-stage{...}`, `::git-commit{...}`, and `::git-push{...}`.
- Convert patch and tool-result dumps into Claude-safe text/tool-result summaries.
- Keep `ai-title` and Claude-3p metadata title aligned.
- Validate JSONL parse and required fields.

7. Repair Claude custom groups when project grouping is wrong.

Install `classic-level` in the scratch directory if it is missing:

```powershell
npm install classic-level
```

Then run:

```powershell
node .\repair_claude_project_groups.js
```

Important implementation details:

- Write custom group names into Chromium Local Storage with JSON ASCII escaping. Raw UTF-8 Chinese can display as `ä¸...` in Claude UI.
- Assign both `local_*` session ids and `cliSessionId` values in `customGroupAssignments`, because Claude UI versions may use either.
- Keep `customGroupOrder` to the visible `local_*` ids only, otherwise the sidebar may duplicate entries.

## Verification Checklist

Run these checks before saying the repair is done.

```powershell
@'
from pathlib import Path
from codex_to_claude_history_import import get_threads, validate_imported, validate_desktop_sessions
threads = [t for t in get_threads() if Path(t["dest"]).exists()]
print(validate_imported(threads))
print(validate_desktop_sessions(threads))
'@ | python -
```

Scan for residual incompatible markers:

```powershell
@'
from pathlib import Path
from codex_to_claude_history_import import get_threads
needles = [
    "<environment_context>",
    "<codex_internal_context",
    "<turn_aborted>",
    "Warning: apply_patch was requested via shell.",
    "::git-stage",
    "::git-commit",
    "::git-push",
    "Imported context event: thread rolled back",
    "Patch apply result",
]
counts = dict.fromkeys(needles, 0)
for t in get_threads():
    p = Path(t["dest"])
    if not p.exists():
        continue
    text = p.read_text(encoding="utf-8", errors="replace")
    for needle in needles:
        counts[needle] += text.count(needle)
for key, value in counts.items():
    print(f"{key}\t{value}")
'@ | python -
```

Verify custom groups at the raw storage level:

```powershell
@'
const path = require("path");
const { ClassicLevel } = require("classic-level");
const home = process.env.USERPROFILE || process.env.HOME;
const dbPath = path.join(home, "AppData", "Local", "Claude-3p", "Local Storage", "leveldb");
(async () => {
  const db = new ClassicLevel(dbPath, { keyEncoding: "utf8", valueEncoding: "utf8" });
  await db.open();
  let dframeKey = null;
  for await (const [key] of db.iterator()) if (String(key).endsWith("dframe-store")) dframeKey = key;
  const raw = await db.get(dframeKey);
  const hasLiteralChinese = /[\u4e00-\u9fff]/.test(raw);
  const hasMojibake = raw.includes("ä¸") || raw.includes("æ") || raw.includes("鍗") || raw.includes("涓");
  const text = String(raw || "");
  const body = text.startsWith("\x01") ? text.slice(1) : text;
  const obj = JSON.parse(body);
  console.log(JSON.stringify({
    hasLiteralChinese,
    hasMojibake,
    mode: obj.state?.groupByByMode?.code,
    groups: obj.state?.customGroups,
    assignmentCount: Object.keys(obj.state?.customGroupAssignments || {}).length,
    orderCounts: Object.fromEntries(Object.entries(obj.state?.customGroupOrder || {}).map(([k, v]) => [k, v.length])),
  }, null, 2));
  await db.close();
})().catch(e => { console.error(e); process.exit(1); });
'@ | node -
```

Expected:

- `validate_imported(...).ok == True`
- `validate_desktop_sessions(...).ok == True`
- Residual incompatible marker counts are all `0`
- `mode` is `custom` when custom grouping is intended
- Group names parse as Chinese, while raw storage has no literal Chinese and no mojibake
- `customGroupOrder` counts match the expected visible thread counts

## Troubleshooting

- If titles are correct in JSONL but wrong in Claude UI, inspect Claude-3p `local_*.json` metadata and update `title` there too.
- If group names read correctly from LevelDB but display as mojibake in UI, rewrite Local Storage values with ASCII-escaped JSON, not raw UTF-8.
- If sessions remain under `Ungrouped`, add both `sessionId` and `cliSessionId` to `customGroupAssignments`.
- If counts double in the sidebar, keep both ids in assignments but only `local_*` ids in `customGroupOrder`.
- If a newly created Codex thread appears in the target cwd after the original migration count, filter polish/validation to already imported destination files unless the user asks to import the new thread.
