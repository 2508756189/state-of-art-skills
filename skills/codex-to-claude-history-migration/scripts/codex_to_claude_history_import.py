#!/usr/bin/env python3
"""Import selected Codex Desktop histories into local Claude history JSONL.

This is intentionally conservative:
- reads Codex state and rollout JSONL only;
- writes deterministic Claude session files so re-runs are idempotent;
- records Codex tool activity as plain searchable text, not Claude tool blocks.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
import uuid
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


HOME = Path.home()
CODEX_DB = HOME / ".codex" / "state_5.sqlite"
CLAUDE_HOME = HOME / ".claude"
CLAUDE_PROJECTS = CLAUDE_HOME / "projects"
CLAUDE_JSON = HOME / ".claude.json"
CLAUDE_3P_HOME = HOME / "AppData" / "Local" / "Claude-3p"
CLAUDE_3P_SESSIONS = CLAUDE_3P_HOME / "claude-code-sessions"
CLAUDE_VERSION = "2.1.165"
CLAUDE_MODEL = "claude-opus-4.8"
IMPORT_NAMESPACE = uuid.UUID("3d5c3fe9-3b2b-54c5-a5f9-95b7d7e06fd8")
IMPORT_MARKER = "Imported from Codex"


BASE = "D:\\" + "\u7535\u52a8\u8f66\u5145\u7535\u5bf9\u63a5\u6587\u6863"
TARGETS = [
    {
        "cwd": BASE + "\\" + "\u7518\u5b5ccpw\u8df3\u677f\u63a5\u4e3b\u5e73\u53f0\u9879\u76ee",
        "slug": "D--------------cpw--------",
        "label": "\u4e30\u6cfd-cpw\u8df3\u677f\u4e3b\u5e73\u53f0\u6a21\u5f0f",
    },
    {
        "cwd": BASE + "\\" + "\u4e3b\u5e73\u53f0\u76f4\u8fde\u6a21\u5f0f",
        "slug": None,
        "label": "\u534e\u6995-\u4e3b\u5e73\u53f0\u76f4\u8fde\u6a21\u5f0f",
    },
]


SKIP_RESPONSE_ITEM_TYPES = {
    "reasoning",
}
SKIP_EVENT_TYPES = {
    "token_count",
    "task_started",
    "context_compacted",
    "turn_aborted",
    "thread_rolled_back",
    "web_search_end",
}
SKIP_ROLES = {
    "system",
    "developer",
}


def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def normalize_path(value: str | None) -> str:
    if not value:
        return ""
    value = value.replace("\\\\?\\", "")
    return value.rstrip("\\/").casefold()


def printable_path(value: str | None) -> str:
    if not value:
        return ""
    return value.replace("\\\\?\\", "")


def path_exists(value: str | None) -> bool:
    return bool(value) and Path(printable_path(value)).exists()


def sanitize_project_slug(path: str) -> str:
    return "".join(ch if ord(ch) < 128 and (ch.isalnum() or ch in "._-") else "-" for ch in path)


def session_id_for_thread(thread_id: str) -> str:
    return str(uuid.uuid5(IMPORT_NAMESPACE, thread_id))


def local_session_id_for_cli_session(session_id: str) -> str:
    return "local_" + str(uuid.uuid5(IMPORT_NAMESPACE, f"local-session:{session_id}"))


def event_uuid(session_id: str, index: int, kind: str = "event") -> str:
    return str(uuid.uuid5(IMPORT_NAMESPACE, f"{session_id}:{kind}:{index}"))


def claude_message_id(session_id: str, index: int) -> str:
    digest = hashlib.sha1(f"{session_id}:{index}".encode("utf-8")).hexdigest()
    return str(int(digest[:13], 16))


def parse_time(value: Any, fallback: str | None = None) -> str:
    if isinstance(value, str) and value:
        if value.endswith("Z"):
            return value
        try:
            parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=dt.timezone.utc)
            return parsed.astimezone(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        except ValueError:
            return value
    if isinstance(value, (int, float)) and value > 0:
        try:
            return dt.datetime.fromtimestamp(value, dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        except (OverflowError, OSError, ValueError):
            pass
    return fallback or utc_now_iso()


def iso_to_epoch_ms(value: str | None, fallback_ms: int | None = None) -> int:
    if value:
        try:
            parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=dt.timezone.utc)
            return int(parsed.timestamp() * 1000)
        except ValueError:
            pass
    if fallback_ms is not None:
        return fallback_ms
    return int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000)


def truncate_text(text: str, limit: int = 12000) -> str:
    if len(text) <= limit:
        return text
    omitted = len(text) - limit
    return text[:limit] + f"\n\n[Codex import note: truncated {omitted} characters from this record]"


def normalize_title_text(value: Any, fallback: str = "\u5386\u53f2\u4f1a\u8bdd", limit: int = 120) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    text = text.strip(" \n\r\t#")
    if not text:
        text = fallback
    if len(text) > limit:
        text = text[: max(1, limit - 3)].rstrip() + "..."
    return text


def display_title_for_thread(thread: dict[str, Any]) -> str:
    raw_title = str(thread.get("title") or "")
    cwd = printable_path(thread.get("target_cwd") or thread.get("cwd"))
    for prefix in (cwd + "\\", cwd + "/"):
        if raw_title.casefold().startswith(prefix.casefold()):
            raw_title = raw_title[len(prefix) :]
            break
    return normalize_title_text(raw_title)


def compact_json(value: Any, limit: int = 8000) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    except TypeError:
        text = str(value)
    return truncate_text(text, limit)


def text_from_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                kind = item.get("type", "content")
                if isinstance(item.get("text"), str):
                    parts.append(item["text"])
                elif isinstance(item.get("input_text"), str):
                    parts.append(item["input_text"])
                elif isinstance(item.get("output_text"), str):
                    parts.append(item["output_text"])
                elif isinstance(item.get("content"), str):
                    parts.append(item["content"])
                else:
                    parts.append(f"[Codex {kind}: {compact_json(item, 2000)}]")
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)
    if isinstance(content, dict):
        if isinstance(content.get("text"), str):
            return content["text"]
        if isinstance(content.get("message"), str):
            return content["message"]
        return compact_json(content, 8000)
    return str(content)


def tool_name_from_payload(payload: dict[str, Any]) -> str:
    return str(payload.get("name") or payload.get("tool") or payload.get("type") or "unknown")


def convert_tool_payload(payload: dict[str, Any]) -> str:
    ptype = payload.get("type", "unknown")
    if ptype in {"function_call", "custom_tool_call", "web_search_call"}:
        name = tool_name_from_payload(payload)
        args = payload.get("arguments", payload.get("input", payload.get("query", {})))
        call_id = payload.get("call_id") or payload.get("id")
        head = f"[Codex tool call: {name}]"
        if call_id:
            head += f" call_id={call_id}"
        return f"{head}\n{compact_json(args)}"
    if ptype in {"function_call_output", "custom_tool_call_output"}:
        call_id = payload.get("call_id") or payload.get("id")
        output = payload.get("output", payload.get("result", payload))
        head = "[Codex tool output]"
        if call_id:
            head += f" call_id={call_id}"
        return f"{head}\n{text_from_content(output) if isinstance(output, str) else compact_json(output)}"
    return f"[Codex event: {ptype}]\n{compact_json(payload)}"


def convert_patch_payload(payload: dict[str, Any]) -> str:
    pieces = ["[Codex patch/apply result]"]
    if "success" in payload:
        pieces.append(f"success={payload.get('success')}")
    stdout = payload.get("stdout")
    stderr = payload.get("stderr")
    if stdout:
        pieces.append("stdout:\n" + text_from_content(stdout))
    if stderr:
        pieces.append("stderr:\n" + text_from_content(stderr))
    changes = payload.get("changes")
    if changes:
        pieces.append("changes:\n" + compact_json(changes, 10000))
    return "\n\n".join(pieces)


def rollout_events(rollout_path: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    with open(printable_path(rollout_path), "r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                events.append(
                    {
                        "timestamp": utc_now_iso(),
                        "role": "assistant",
                        "text": f"[Codex import parse warning: line {line_no} is not JSON: {exc}]",
                    }
                )
                continue
            etype = obj.get("type")
            payload = obj.get("payload")
            ts = parse_time(obj.get("timestamp"))
            if etype == "response_item" and isinstance(payload, dict):
                ptype = payload.get("type")
                if ptype in SKIP_RESPONSE_ITEM_TYPES:
                    continue
                if ptype == "message":
                    role = payload.get("role")
                    if role in SKIP_ROLES:
                        continue
                    if role not in {"user", "assistant"}:
                        continue
                    text = text_from_content(payload.get("content"))
                    if text.strip():
                        events.append({"timestamp": ts, "role": role, "text": text})
                    continue
                if ptype in {"function_call", "function_call_output", "custom_tool_call", "custom_tool_call_output", "web_search_call"}:
                    text = convert_tool_payload(payload)
                    if text.strip():
                        events.append({"timestamp": ts, "role": "assistant", "text": text})
                    continue
                text = f"[Codex response item: {ptype}]\n{compact_json(payload)}"
                events.append({"timestamp": ts, "role": "assistant", "text": text})
            elif etype == "event_msg" and isinstance(payload, dict):
                ptype = payload.get("type")
                if ptype in SKIP_EVENT_TYPES:
                    continue
                if ptype == "user_message":
                    text = text_from_content(payload.get("message"))
                    if text.strip():
                        events.append({"timestamp": ts, "role": "user", "text": text})
                    continue
                if ptype == "agent_message":
                    text = text_from_content(payload.get("message"))
                    if text.strip():
                        events.append({"timestamp": ts, "role": "assistant", "text": text})
                    continue
                if ptype == "patch_apply_end":
                    events.append({"timestamp": ts, "role": "assistant", "text": convert_patch_payload(payload)})
                    continue
                if ptype == "task_complete":
                    text = text_from_content(payload.get("last_agent_message") or payload.get("message"))
                    if text.strip():
                        events.append({"timestamp": ts, "role": "assistant", "text": text})
                    continue
                if ptype in {"context_compacted", "turn_aborted", "thread_rolled_back", "web_search_end"}:
                    text = f"[Codex event: {ptype}]\n{compact_json(payload)}"
                    events.append({"timestamp": ts, "role": "assistant", "text": text})
                    continue
            elif etype == "compacted":
                text = ""
                if isinstance(payload, dict):
                    text = text_from_content(payload.get("summary") or payload.get("text") or payload)
                if text.strip():
                    events.append({"timestamp": ts, "role": "assistant", "text": f"[Codex compacted context]\n{text}"})
    return dedupe_events(events)


def dedupe_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    recent: list[tuple[str, str]] = []
    for event in events:
        role = event["role"]
        text = re.sub(r"\s+", " ", event["text"]).strip()
        if not text:
            continue
        key = (role, text)
        if key in recent[-5:]:
            continue
        deduped.append(event)
        recent.append(key)
        if len(recent) > 20:
            recent = recent[-20:]
    return deduped


def make_user_record(session_id: str, parent_uuid: str | None, index: int, cwd: str, timestamp: str, text: str) -> dict[str, Any]:
    return {
        "parentUuid": parent_uuid,
        "isSidechain": False,
        "type": "user",
        "message": {"role": "user", "content": truncate_text(text)},
        "uuid": event_uuid(session_id, index, "user"),
        "timestamp": timestamp,
        "permissionMode": "acceptEdits",
        "promptSource": "sdk",
        "userType": "external",
        "entrypoint": "codex-import",
        "cwd": cwd,
        "sessionId": session_id,
        "version": CLAUDE_VERSION,
        "gitBranch": "",
    }


def make_assistant_record(session_id: str, parent_uuid: str | None, index: int, cwd: str, timestamp: str, text: str) -> dict[str, Any]:
    return {
        "parentUuid": parent_uuid,
        "isSidechain": False,
        "message": {
            "id": claude_message_id(session_id, index),
            "type": "message",
            "role": "assistant",
            "model": CLAUDE_MODEL,
            "content": [{"type": "text", "text": truncate_text(text)}],
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {
                "input_tokens": 0,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
                "output_tokens": 0,
                "server_tool_use": {"web_search_requests": 0, "web_fetch_requests": 0},
                "service_tier": "standard",
            },
        },
        "type": "assistant",
        "uuid": event_uuid(session_id, index, "assistant"),
        "timestamp": timestamp,
        "userType": "external",
        "entrypoint": "codex-import",
        "cwd": cwd,
        "sessionId": session_id,
        "version": CLAUDE_VERSION,
        "gitBranch": "",
    }


def make_title_record(session_id: str, title: str) -> dict[str, Any]:
    safe_title = normalize_title_text(title, fallback="Imported Codex conversation", limit=180)
    return {
        "type": "ai-title",
        "aiTitle": safe_title,
        "sessionId": session_id,
        "uuid": event_uuid(session_id, 0, "title"),
        "timestamp": utc_now_iso(),
        "cwd": "",
    }


def make_import_records(thread: dict[str, Any], cwd: str) -> list[dict[str, Any]]:
    session_id = session_id_for_thread(thread["id"])
    intro = "\n".join(
        [
            IMPORT_MARKER,
            f"Codex thread id: {thread['id']}",
            f"Original title: {thread.get('title') or ''}",
            f"Original cwd: {printable_path(thread.get('cwd'))}",
            f"Archived in Codex: {bool(thread.get('archived'))}",
            f"Rollout path: {printable_path(thread.get('rollout_path'))}",
            "",
            "Tool calls, tool outputs, patches, web search activity, and MCP/function calls are imported as plain searchable text records.",
        ]
    )
    source_events = rollout_events(thread["rollout_path"])
    base_ts = parse_time(thread.get("updated_at"))
    records: list[dict[str, Any]] = [make_title_record(session_id, display_title_for_thread(thread))]
    parent: str | None = None
    first = make_user_record(session_id, parent, 1, cwd, source_events[0]["timestamp"] if source_events else base_ts, intro)
    records.append(first)
    parent = first["uuid"]
    for offset, event in enumerate(source_events, start=2):
        if event["role"] == "user":
            rec = make_user_record(session_id, parent, offset, cwd, event["timestamp"], event["text"])
        else:
            rec = make_assistant_record(session_id, parent, offset, cwd, event["timestamp"], event["text"])
        records.append(rec)
        parent = rec["uuid"]
    return records


def get_threads() -> list[dict[str, Any]]:
    targets_by_norm = {normalize_path(t["cwd"]): t for t in TARGETS}
    con = sqlite3.connect(CODEX_DB)
    con.row_factory = sqlite3.Row
    rows: list[dict[str, Any]] = []
    for row in con.execute("select id,title,cwd,archived,rollout_path,updated_at,created_at from threads"):
        target = targets_by_norm.get(normalize_path(row["cwd"]))
        if not target:
            continue
        item = dict(row)
        item["target_cwd"] = target["cwd"]
        item["target_slug"] = target["slug"] or sanitize_project_slug(target["cwd"])
        item["target_label"] = target.get("label") or item["target_slug"]
        item["session_id"] = session_id_for_thread(item["id"])
        item["dest"] = str(CLAUDE_PROJECTS / item["target_slug"] / f"{item['session_id']}.jsonl")
        item["rollout_exists"] = path_exists(item.get("rollout_path"))
        rows.append(item)
    con.close()
    return sorted(rows, key=lambda r: (r.get("updated_at") or 0, r["id"]), reverse=True)


def existing_import(path: Path, thread_id: str) -> bool:
    if not path.exists():
        return False
    try:
        session_id = path.stem
        session_dir = discover_claude_3p_session_dir()
        if session_dir is not None:
            meta_path = session_dir / f"{local_session_id_for_cli_session(session_id)}.json"
            if meta_path.exists():
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                if meta.get("cliSessionId") == session_id and meta.get("codexImport", {}).get("threadId") == thread_id:
                    return True
    except Exception:
        pass
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for _ in range(5):
                line = handle.readline()
                if not line:
                    break
                if thread_id in line and IMPORT_MARKER in line:
                    return True
    except OSError:
        return False
    return False


def ensure_backup() -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = CLAUDE_HOME / "backups" / f"codex-import-{stamp}"
    dest.mkdir(parents=True, exist_ok=False)
    if CLAUDE_PROJECTS.exists():
        shutil.copytree(CLAUDE_PROJECTS, dest / "projects")
    if CLAUDE_JSON.exists():
        shutil.copy2(CLAUDE_JSON, dest / ".claude.json")
    if CLAUDE_3P_SESSIONS.exists():
        shutil.copytree(CLAUDE_3P_SESSIONS, dest / "claude-code-sessions")
    return dest


def default_project_entry() -> dict[str, Any]:
    return {
        "allowedTools": [],
        "mcpContextUris": [],
        "enabledMcpjsonServers": [],
        "disabledMcpjsonServers": [],
        "hasTrustDialogAccepted": True,
        "projectOnboardingSeenCount": 0,
        "hasClaudeMdExternalIncludesApproved": False,
        "hasClaudeMdExternalIncludesWarningShown": False,
    }


def update_claude_json() -> bool:
    data: dict[str, Any]
    if CLAUDE_JSON.exists():
        with open(CLAUDE_JSON, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    else:
        data = {}
    projects = data.setdefault("projects", {})
    changed = False
    for target in TARGETS:
        cwd = target["cwd"]
        if cwd not in projects:
            projects[cwd] = default_project_entry()
            changed = True
        else:
            entry = projects[cwd]
            for key, value in default_project_entry().items():
                if key not in entry:
                    entry[key] = value
                    changed = True
            if entry.get("hasTrustDialogAccepted") is not True:
                entry["hasTrustDialogAccepted"] = True
                changed = True
    if changed:
        with open(CLAUDE_JSON, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    return changed


def dry_run(threads: list[dict[str, Any]]) -> dict[str, Any]:
    by_project = Counter((t["target_slug"], int(t["archived"])) for t in threads)
    missing = [t for t in threads if not t["rollout_exists"]]
    details = []
    for thread in threads:
        dest = Path(thread["dest"])
        try:
            count = len(rollout_events(thread["rollout_path"])) + 2
        except Exception as exc:  # noqa: BLE001 - report all dry-run blockers
            count = f"ERROR: {exc}"
        details.append(
            {
                "id": thread["id"],
                "archived": bool(thread["archived"]),
                "rollout_exists": thread["rollout_exists"],
                "project_slug": thread["target_slug"],
                "dest_exists": dest.exists(),
                "estimated_records": count,
            }
        )
    return {
        "candidate_count": len(threads),
        "by_project_archived": {f"{slug}|archived={archived}": count for (slug, archived), count in by_project.items()},
        "missing_rollout_count": len(missing),
        "details": details,
    }


def pick_canary_threads(threads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    picked = []
    seen = set()
    for thread in threads:
        slug = thread["target_slug"]
        if slug in seen:
            continue
        picked.append(thread)
        seen.add(slug)
    return picked


def write_threads(threads: list[dict[str, Any]]) -> dict[str, Any]:
    written = []
    skipped = []
    for thread in threads:
        dest = Path(thread["dest"])
        if existing_import(dest, thread["id"]):
            skipped.append({"id": thread["id"], "dest": str(dest), "reason": "already_imported"})
            continue
        if dest.exists():
            skipped.append({"id": thread["id"], "dest": str(dest), "reason": "existing_non_import_file"})
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        records = make_import_records(thread, thread["target_cwd"])
        with open(dest, "w", encoding="utf-8", newline="\n") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
                handle.write("\n")
        written.append({"id": thread["id"], "dest": str(dest), "records": len(records)})
    return {"written": written, "skipped": skipped}


def validate_file(path: Path) -> tuple[bool, str, int]:
    count = 0
    session_id = None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                obj = json.loads(line)
                count += 1
                for key in ("sessionId", "uuid", "type", "timestamp", "cwd"):
                    if key not in obj:
                        return False, f"{path}: line {line_no} missing {key}", count
                if session_id is None:
                    session_id = obj["sessionId"]
                elif obj["sessionId"] != session_id:
                    return False, f"{path}: line {line_no} sessionId mismatch", count
    except Exception as exc:  # noqa: BLE001
        return False, f"{path}: {exc}", count
    return True, "ok", count


def validate_imported(threads: list[dict[str, Any]]) -> dict[str, Any]:
    results = []
    ok = True
    total_records = 0
    imported_count = 0
    for thread in threads:
        path = Path(thread["dest"])
        if not path.exists():
            ok = False
            results.append({"id": thread["id"], "ok": False, "message": "missing_file", "records": 0})
            continue
        valid, message, records = validate_file(path)
        total_records += records
        imported_count += 1
        ok = ok and valid
        results.append({"id": thread["id"], "ok": valid, "message": message, "records": records})
    return {
        "ok": ok,
        "imported_file_count": imported_count,
        "expected_file_count": len(threads),
        "total_records": total_records,
        "failures": [r for r in results if not r["ok"]],
    }


def discover_claude_3p_session_dir() -> Path | None:
    if not CLAUDE_3P_SESSIONS.exists():
        return None
    candidates = []
    for account_dir in CLAUDE_3P_SESSIONS.iterdir():
        if not account_dir.is_dir():
            continue
        for org_dir in account_dir.iterdir():
            if org_dir.is_dir():
                candidates.append(org_dir)
    if len(candidates) == 1:
        return candidates[0]
    if candidates:
        return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[0]
    return None


def imported_file_summary(path: Path) -> dict[str, Any]:
    first_ts = None
    last_ts = None
    user_count = 0
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            obj = json.loads(line)
            ts = obj.get("timestamp")
            if ts:
                if first_ts is None:
                    first_ts = ts
                last_ts = ts
            if obj.get("type") == "user":
                user_count += 1
    return {
        "createdAt": iso_to_epoch_ms(first_ts),
        "lastActivityAt": iso_to_epoch_ms(last_ts, iso_to_epoch_ms(first_ts)),
        "completedTurns": max(1, user_count),
    }


def default_enabled_mcp_tools() -> dict[str, bool]:
    return {
        "local:mcp-registry:search_mcp_registry": False,
        "local:mcp-registry:suggest_connectors": False,
        "local:plugins:suggest_plugin_install": False,
        "local:plugins:search_plugins": False,
        "local:plugins:list_plugins": False,
    }


def ui_path(value: str) -> str:
    return printable_path(value).replace("\\", "/")


def make_desktop_session_metadata(thread: dict[str, Any], dest_file: Path) -> dict[str, Any]:
    summary = imported_file_summary(dest_file)
    cli_session_id = thread["session_id"]
    title = display_title_for_thread(thread)
    project_label = thread.get("target_label") or thread["target_slug"]
    return {
        "sessionId": local_session_id_for_cli_session(cli_session_id),
        "cliSessionId": cli_session_id,
        "title": title,
        "initialMessage": normalize_title_text(thread.get("title"), limit=2000),
        "cwd": thread["target_cwd"],
        "originCwd": thread["target_cwd"],
        "userSelectedFolders": [ui_path(thread["target_cwd"])],
        "projectName": project_label,
        "projectPath": thread["target_cwd"],
        "workspaceRoot": thread["target_cwd"],
        "lastFocusedAt": summary["lastActivityAt"],
        "createdAt": summary["createdAt"],
        "lastActivityAt": summary["lastActivityAt"],
        "model": "claude-opus-4-8",
        "effort": "high",
        "sessionSettings": {"ultracode": False},
        "isArchived": bool(thread.get("archived")),
        "permissionMode": "bypassPermissions",
        "enabledMcpTools": default_enabled_mcp_tools(),
        "remoteMcpServersConfig": [],
        "chromePermissionMode": "skip_all_permission_checks",
        "completedTurns": summary["completedTurns"],
        "alwaysAllowedReasons": [],
        "sessionPermissionUpdates": [],
        "classifierSummaryEnabled": False,
        "codexImport": {
            "threadId": thread["id"],
            "projectSlug": thread["target_slug"],
            "projectName": project_label,
            "cwd": thread["target_cwd"],
        },
    }


def write_desktop_sessions(threads: list[dict[str, Any]]) -> dict[str, Any]:
    session_dir = discover_claude_3p_session_dir()
    if session_dir is None:
        return {"ok": False, "session_dir": None, "written": [], "skipped": [], "error": "claude_3p_session_dir_not_found"}
    written = []
    skipped = []
    session_dir.mkdir(parents=True, exist_ok=True)
    for thread in threads:
        transcript = Path(thread["dest"])
        if not transcript.exists():
            skipped.append({"id": thread["id"], "reason": "missing_transcript"})
            continue
        metadata = make_desktop_session_metadata(thread, transcript)
        path = session_dir / f"{metadata['sessionId']}.json"
        if path.exists():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
                if existing.get("cliSessionId") == metadata["cliSessionId"]:
                    changed = False
                    for key, value in metadata.items():
                        if existing.get(key) != value:
                            existing[key] = value
                            changed = True
                    if changed:
                        path.write_text(json.dumps(existing, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
                        written.append({"id": thread["id"], "path": str(path), "cliSessionId": metadata["cliSessionId"], "updated": "metadata"})
                        continue
                    skipped.append({"id": thread["id"], "reason": "already_exists", "path": str(path)})
                    continue
            except json.JSONDecodeError:
                pass
            skipped.append({"id": thread["id"], "reason": "existing_non_matching_file", "path": str(path)})
            continue
        path.write_text(json.dumps(metadata, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        written.append({"id": thread["id"], "path": str(path), "cliSessionId": metadata["cliSessionId"]})
    return {"ok": True, "session_dir": str(session_dir), "written": written, "skipped": skipped}


def validate_desktop_sessions(threads: list[dict[str, Any]]) -> dict[str, Any]:
    session_dir = discover_claude_3p_session_dir()
    if session_dir is None:
        return {"ok": False, "error": "claude_3p_session_dir_not_found", "expected": len(threads), "present": 0, "failures": []}
    failures = []
    present = 0
    for thread in threads:
        cli_session_id = thread["session_id"]
        local_id = local_session_id_for_cli_session(cli_session_id)
        path = session_dir / f"{local_id}.json"
        if not path.exists():
            failures.append({"id": thread["id"], "reason": "missing_metadata", "path": str(path)})
            continue
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append({"id": thread["id"], "reason": f"json_parse_error: {exc}", "path": str(path)})
            continue
        present += 1
        for key in ("sessionId", "cliSessionId", "cwd", "createdAt", "lastActivityAt", "model", "effort"):
            if key not in obj:
                failures.append({"id": thread["id"], "reason": f"missing_{key}", "path": str(path)})
                break
        if obj.get("cliSessionId") != cli_session_id:
            failures.append({"id": thread["id"], "reason": "cliSessionId_mismatch", "path": str(path)})
    return {"ok": not failures and present == len(threads), "session_dir": str(session_dir), "expected": len(threads), "present": present, "failures": failures}


def print_json(label: str, value: Any) -> None:
    print(f"== {label} ==")
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--canary", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--idempotency-check", action="store_true")
    parser.add_argument("--desktop-sessions", action="store_true")
    parser.add_argument("--validate-desktop-sessions", action="store_true")
    args = parser.parse_args()

    if not CODEX_DB.exists():
        print(f"Codex DB not found: {CODEX_DB}", file=sys.stderr)
        return 2

    threads = get_threads()
    if args.dry_run:
        report = dry_run(threads)
        # Keep the dry-run useful but not too leaky: no titles or content previews.
        print_json("dry_run", report)

    selected: list[dict[str, Any]] = []
    if args.canary:
        selected = pick_canary_threads(threads)
    elif args.full:
        selected = threads

    if selected:
        backup = ensure_backup()
        write_report = write_threads(selected)
        changed_claude_json = update_claude_json()
        validation = validate_imported(selected)
        print_json(
            "write",
            {
                "mode": "canary" if args.canary else "full",
                "backup": str(backup),
                "selected_count": len(selected),
                "written_count": len(write_report["written"]),
                "skipped_count": len(write_report["skipped"]),
                "changed_claude_json": changed_claude_json,
                "write_report": write_report,
                "validation": validation,
            },
        )
        if not validation["ok"]:
            return 3

    if args.desktop_sessions:
        backup = ensure_backup()
        report = write_desktop_sessions(threads)
        validation = validate_desktop_sessions(threads)
        print_json("desktop_sessions", {"backup": str(backup), "write_report": report, "validation": validation})
        if not validation["ok"]:
            return 4

    if args.validate:
        print_json("validate", validate_imported(threads))

    if args.validate_desktop_sessions:
        print_json("validate_desktop_sessions", validate_desktop_sessions(threads))

    if args.idempotency_check:
        existing = 0
        missing = 0
        non_import = 0
        for thread in threads:
            path = Path(thread["dest"])
            if existing_import(path, thread["id"]):
                existing += 1
            elif path.exists():
                non_import += 1
            else:
                missing += 1
        print_json("idempotency", {"already_imported": existing, "missing": missing, "existing_non_import": non_import, "total": len(threads)})

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
