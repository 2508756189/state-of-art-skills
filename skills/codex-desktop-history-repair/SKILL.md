---
name: codex-desktop-history-repair
description: "Use when Codex Desktop history, providers, projects, pinned threads, or migrated conversations do not show correctly. Covers state_5.sqlite threads, rollout JSONL session_meta, session_index.jsonl, .codex-global-state.json, model_provider migration, projectless-thread-ids, electron-saved-workspace-roots, project-order, active-workspace-roots, and Windows path/encoding issues."
---

# Codex Desktop History Repair

Use this skill to diagnose and repair Codex Desktop history visibility problems. Common cases:

- Conversations moved from `openai` to a custom provider do not appear.
- Changing `[model_providers.*].name` did not change history grouping.
- Threads show only when pinned, disappear after unpinning, or appear under "no project".
- A project exists in `config.toml` but does not show in the left sidebar.
- A rollout JSONL exists, but the UI does not list the conversation.

## Mental model

Codex Desktop history is controlled by several layers. Do not treat one file as the whole truth.

- Provider identity: `state_5.sqlite` table `threads.model_provider`, plus the first `session_meta.payload.model_provider` in each rollout JSONL.
- Complete conversation content: `sessions/**/rollout-*.jsonl` and `archived_sessions/rollout-*.jsonl`.
- Sidebar thread index: `state_5.sqlite`, `.codex-global-state.json`, and sometimes `session_index.jsonl`.
- Project trust: `config.toml [projects]`.
- Project sidebar visibility: `.codex-global-state.json` fields `electron-saved-workspace-roots` and `project-order`.
- Current workspace filters: `.codex-global-state.json` fields `active-workspace-roots`, `thread-workspace-root-hints`, and `projectless-thread-ids`.

`[model_providers.<key>].name` is a display label. The durable identifier is the provider key, such as `openai` or `custom`.

## Safety rules

1. Back up before editing:
   - `$CODEX_HOME/state_5.sqlite`
   - `$CODEX_HOME/.codex-global-state.json`
   - `$CODEX_HOME/session_index.jsonl`
   - affected rollout JSONL files
2. Use the SQLite backup API rather than copying a live database file when Codex may be running.
3. Do not expose API keys, passwords, or production secrets from thread titles, previews, or rollout content.
4. On Windows, read/write JSON with UTF-8 and preserve Chinese paths. Prefer Python JSON parsing over text replacement.
5. For project sidebar repairs, close Codex Desktop first. The Electron process rewrites `.codex-global-state.json` and can undo online edits.

## Diagnose

Find provider counts and candidate threads:

```powershell
@'
import sqlite3, json, os
con = sqlite3.connect(os.path.join(os.path.expanduser("~"), ".codex", "state_5.sqlite"))
con.row_factory = sqlite3.Row
for r in con.execute("select model_provider, archived, count(*) from threads group by model_provider, archived"):
    print(r)
for r in con.execute("select id,title,model_provider,cwd,archived,rollout_path from threads order by updated_at desc limit 20"):
    print(json.dumps(dict(r), ensure_ascii=False))
con.close()
'@ | python -
```

Check whether the official app index sees a thread. Prefer Codex app thread tools when available:

- `list_threads` with no query to see what the app currently indexes.
- `list_threads` with `query` such as a title keyword, `RVC_model`, or `docker-compose`.

Interpretation:

- If `list_threads` sees the thread but the UI does not, the issue is a UI filter or saved-project list.
- If pinned threads show but unpinned threads disappear, the issue is project/workspace filtering.
- If `config.toml [projects]` contains a path but the left sidebar does not, the missing layer is usually `.codex-global-state.json` `electron-saved-workspace-roots` / `project-order`.

## Migrate Provider

To move unarchived conversations from one provider key to another, update both the database and rollout metadata.

1. Select only the intended rows:

```sql
select id, title, rollout_path
from threads
where model_provider = 'openai' and archived = 0;
```

2. Update `threads.model_provider`.
3. For each rollout file, parse the first line as JSON and update `payload.model_provider`.
4. Verify:

```sql
select model_provider, archived, count(*)
from threads
group by model_provider, archived;
```

Never rely on changing `[model_providers.<key>].name`; it does not migrate history.

## Repair Thread Visibility

For a thread to appear and load correctly:

- `threads.id` must match the rollout first-line `session_meta.payload.id`.
- `threads.rollout_path` must point to an existing rollout JSONL.
- `threads.model_provider` should match the rollout `payload.model_provider`.
- `threads.archived = 0` for unarchived lists.
- `threads.cwd` should match the intended project root.
- `.codex-global-state.json` should not put a real project thread in `projectless-thread-ids`.
- `thread-workspace-root-hints[thread_id]` should point to the intended project root.

If the user wants a thread to stay in its original project, keep `threads.cwd` as the original root. Do not change it to the current project just to make it appear in one sidebar.

## Repair Project Sidebar

If a project exists on disk and in `config.toml` but is missing from the left sidebar, add it to `.codex-global-state.json`:

- `electron-saved-workspace-roots`
- `project-order`
- optionally `active-workspace-roots`

Important: Codex Desktop must be fully closed before this edit, otherwise Electron may overwrite the file. Use `scripts/add_codex_desktop_projects.ps1` after exiting Codex.

Example:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\add_codex_desktop_projects.ps1 `
  -Roots 'E:\RVC_model','E:\软考-资料','D:\党小组会学习材料'
```

If the shell mangles Chinese path arguments, put paths in a UTF-8 file and use `-RootsFile`:

```json
[
  "E:\\RVC_model",
  "E:\\软考-资料",
  "D:\\党小组会学习材料"
]
```

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\add_codex_desktop_projects.ps1 `
  -RootsFile .\roots.json
```

Then restart Codex Desktop.

## Verification Checklist

- `config.toml` parses as TOML.
- `.codex-global-state.json` parses as JSON.
- `list_threads` finds the expected threads by title or path keyword.
- The thread is not in `projectless-thread-ids` unless it is intentionally projectless.
- The desired project root appears in `electron-saved-workspace-roots` and `project-order`.
- After restarting Codex Desktop, the left sidebar shows the project and its threads.
