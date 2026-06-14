#!/usr/bin/env python3
"""Polish imported Codex histories for Claude UI grouping and readable titles."""

from __future__ import annotations

import json
import re
import uuid
import datetime as dt
from pathlib import Path
from typing import Any

from codex_to_claude_history_import import (
    IMPORT_NAMESPACE,
    TARGETS,
    display_title_for_thread,
    ensure_backup,
    discover_claude_3p_session_dir,
    get_threads,
    local_session_id_for_cli_session,
    normalize_path,
    normalize_title_text,
    ui_path,
    validate_imported,
    validate_desktop_sessions,
)


TITLE_OVERRIDES = Path(__file__).with_name("claude_import_title_overrides.json")

PROJECT_LABELS = {
    (
        target.get("slug")
        or "".join(ch if ord(ch) < 128 and (ch.isalnum() or ch in "._-") else "-" for ch in target["cwd"])
    ): target.get("label")
    for target in TARGETS
}

OLD_TITLE_PREFIXES = {
    "D--------------cpw--------": "甘孜CPW - ",
    "D-------------------": "主平台直连 - ",
}


DROP_TEXT_PREFIXES = (
    "<environment_context>",
    "<codex_internal_context",
    "<turn_aborted>",
    "Warning: apply_patch was requested via shell.",
    "# AGENTS.md instructions",
    "<INSTRUCTIONS>",
    "Imported context event:",
    "Compacted context",
    "Imported response item:",
)

MAX_TOOL_RESULT_CHARS = 20000
TOOL_RESULT_HEAD_CHARS = 12000
TOOL_RESULT_TAIL_CHARS = 4000
SHELL_OUTPUT_RE = re.compile(r"\A\s*Exit code: (-?\d+)\nWall time: ([^\n]+)\n(?:Total output lines: [^\n]+\n)?Output:\n(.*)\Z", re.S)


def strip_xml_block(text: str, tag: str) -> str:
    return re.sub(rf"<{tag}\b[^>]*>.*?</{tag}>", "", text, flags=re.S).strip()


def remove_internal_blocks(text: str) -> str:
    for tag in ("environment_context", "oai-mem-citation", "turn_aborted", "codex_internal_context"):
        text = strip_xml_block(text, tag)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_import_labels(text: str) -> str:
    return (
        text.replace("Imported Codex shell command", "Run shell command")
        .replace("Imported Codex patch", "Apply patch")
        .replace("Imported Node REPL execution", "Run Node.js snippet")
        .replace("apply_patch verification failed:", "Patch verification failed:")
    )


def clean_files_mentioned(text: str) -> str:
    if "# Files mentioned by the user:" not in text:
        return text
    request_match = re.search(r"## My request for Codex:\s*(.*)\Z", text, flags=re.S)
    request = request_match.group(1).strip() if request_match else ""

    file_lines: list[str] = []
    for match in re.finditer(r"##\s+(.+?):\s+([^\n]+)", text):
        name, path = match.group(1).strip(), match.group(2).strip()
        if name == "My request for Codex":
            continue
        file_lines.append(f"- {name}: {path}")

    if not request:
        request = re.sub(r"# Files mentioned by the user:\s*", "", text).strip()

    if file_lines:
        return request + "\n\nReferenced files:\n" + "\n".join(file_lines)
    return request


def clean_text(text: str) -> str:
    text = remove_internal_blocks(text)
    text = re.sub(
        r"(?m)^\s*Warning: apply_patch was requested via shell\. Use the apply_patch tool instead of exec_command\.\s*$\n?",
        "",
        text,
    )
    text = re.sub(r"(?m)^\s*::[A-Za-z0-9_-]+\{[^\n\r]*\}\s*$\n?", "", text)
    text = clean_files_mentioned(text)
    text = remove_internal_blocks(text)
    text = normalize_import_labels(text)
    text = re.sub(r"\n?<image name=\[Image #[^\]]+\]>\n?", "\nImage attachment from original Codex turn was not migrated.\n", text)
    text = re.sub(r"\[Codex input_image: \{.*?\}\]", "Image attachment from original Codex turn was not migrated.", text, flags=re.S)
    text = re.sub(r"\[Codex input_image[^\n\r]*", "Image attachment from original Codex turn was not migrated.", text)
    text = re.sub(r"\]\]\s*</image>", "", text)
    text = text.replace("</image>", "")
    text = re.sub(r"data:image/[^\"'\\\s]+", "data:image/<omitted>", text)
    text = text.replace("# Files mentioned by the user:", "Referenced files:")
    text = text.replace("## My request for Codex:", "Original request:")
    text = text.replace("Codex import:", "")
    text = re.sub(r"(Image attachment from original Codex turn was not migrated\.\s*){2,}", "Image attachment from original Codex turn was not migrated.\n", text)
    return text.strip()


def single_tool_use(record: dict[str, Any]) -> dict[str, str] | None:
    msg = record.get("message")
    if not isinstance(msg, dict):
        return None
    content = msg.get("content")
    if record.get("type") != "assistant" or not isinstance(content, list) or len(content) != 1:
        return None
    item = content[0]
    if not isinstance(item, dict) or item.get("type") != "tool_use":
        return None
    tool_id = item.get("id")
    if not isinstance(tool_id, str) or not tool_id:
        return None
    return {"tool_use_id": tool_id, "assistant_uuid": str(record.get("uuid") or "")}


def summarize_patch_result(text: str) -> tuple[str, bool]:
    success_match = re.search(r"\bsuccess=(True|False|true|false)\b", text)
    success = success_match.group(1).lower() == "true" if success_match else "verification failed" not in text.lower()
    is_error = not success

    stdout_match = re.search(r"\nstdout:\n(.*?)(?:\n\nchanges:\n|\Z)", text, flags=re.S)
    stdout = stdout_match.group(1).strip() if stdout_match else ""

    files: list[str] = []
    in_updated_files = False
    for line in stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("Success. Updated the following files"):
            in_updated_files = True
            continue
        if in_updated_files:
            if not stripped:
                break
            if re.match(r"^[AMDCR]\s+", stripped):
                files.append(stripped)

    changes_match = re.search(r"\nchanges:\n(.*)\Z", text, flags=re.S)
    if changes_match and not files:
        try:
            changes = json.loads(changes_match.group(1))
            if isinstance(changes, dict):
                for path, info in changes.items():
                    prefix = "M"
                    if isinstance(info, dict):
                        typ = str(info.get("type") or "update")
                        prefix = {"add": "A", "delete": "D", "move": "R", "update": "M"}.get(typ, "M")
                    files.append(f"{prefix} {path}")
        except json.JSONDecodeError:
            pass

    lines = ["Patch applied successfully." if success else "Patch application failed."]
    lines.append(f"success={'True' if success else 'False'}")
    if files:
        lines.append("")
        lines.append("Updated files:")
        lines.extend(f"- {item}" for item in files[:30])
        if len(files) > 30:
            lines.append(f"- ... {len(files) - 30} more file(s)")
    elif stdout:
        compact_stdout = re.sub(r"\n{3,}", "\n\n", stdout)
        lines.append("")
        lines.append(compact_stdout[:2000])
        if len(compact_stdout) > 2000:
            lines.append(f"... truncated {len(compact_stdout) - 2000} characters")
    if "unified_diff" in text:
        lines.append("")
        lines.append("Unified diff omitted from the imported Claude transcript; the original Codex rollout keeps the full patch detail.")
    return "\n".join(lines).strip(), is_error


def normalize_shell_output(text: str) -> str:
    match = SHELL_OUTPUT_RE.match(text)
    if not match:
        return re.sub(r"\n?Total output lines: \d+\n", "\n", text).strip()
    exit_code = int(match.group(1))
    body = match.group(3).strip()
    if exit_code == 0:
        return body
    return f"Command exited with code {exit_code}.\n{body}".strip()


def unwrap_json_output(text: str) -> str:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return text
    if isinstance(parsed, dict) and isinstance(parsed.get("output"), str):
        return parsed["output"]
    return text


def omit_codex_instruction_dump_lines(text: str) -> str:
    markers = (
        "base_instructions",
        "developer_instructions",
        "system_instructions",
        "You are Codex, a coding agent",
    )
    lines = text.splitlines()
    kept: list[str] = []
    removed = 0
    for line in lines:
        if any(marker in line for marker in markers):
            removed += 1
            continue
        kept.append(line)
    if removed:
        kept.append(f"[Codex system/developer instruction dump omitted from imported Claude transcript: {removed} line(s).]")
    return "\n".join(kept).strip()


def truncate_tool_output(text: str) -> str:
    if len(text) <= MAX_TOOL_RESULT_CHARS:
        return text
    omitted = len(text) - TOOL_RESULT_HEAD_CHARS - TOOL_RESULT_TAIL_CHARS
    if omitted <= 0:
        return text
    return (
        text[:TOOL_RESULT_HEAD_CHARS].rstrip()
        + f"\n\n[Long tool output truncated for Claude import: omitted {omitted} characters.]\n\n"
        + text[-TOOL_RESULT_TAIL_CHARS:].lstrip()
    )


def clean_tool_result_content(text: str) -> tuple[str, bool]:
    if text.strip().startswith("Patch apply result"):
        return summarize_patch_result(text)
    text = unwrap_json_output(text)
    text = normalize_shell_output(text)
    text = remove_internal_blocks(text)
    text = normalize_import_labels(text)
    text = omit_codex_instruction_dump_lines(text)
    text = re.sub(r"data:image/[^\"'\\\s]+", "data:image/<omitted>", text)
    text = truncate_tool_output(text.strip())
    return text, False


def set_user_tool_result(record: dict[str, Any], tool_id: str, output: str, assistant_uuid: str | None, is_error: bool) -> None:
    msg = record.setdefault("message", {})
    for key in ("id", "type", "model", "stop_reason", "stop_sequence", "usage", "stop_details"):
        msg.pop(key, None)
    msg["role"] = "user"
    msg["content"] = [{"type": "tool_result", "tool_use_id": tool_id, "content": output, "is_error": bool(is_error)}]
    record["type"] = "user"
    if assistant_uuid:
        record["sourceToolAssistantUUID"] = assistant_uuid
    record["toolUseResult"] = {"interrupted": False, "isImage": False, "content": output, "is_error": bool(is_error)}


def clean_tool_results(record: dict[str, Any]) -> int:
    msg = record.get("message")
    changed = 0
    if not isinstance(msg, dict):
        content = None
    else:
        content = msg.get("content")
    if isinstance(content, list):
        for item in content:
            if not isinstance(item, dict) or item.get("type") != "tool_result":
                continue
            raw = item.get("content")
            if not isinstance(raw, str):
                continue
            cleaned, is_error = clean_tool_result_content(raw)
            if cleaned != raw:
                item["content"] = cleaned
                changed += 1
            if is_error and not item.get("is_error"):
                item["is_error"] = True
                changed += 1

    shadow = record.get("toolUseResult")
    if isinstance(shadow, dict):
        for key in ("content", "stdout", "stderr"):
            raw = shadow.get(key)
            if not isinstance(raw, str):
                continue
            cleaned, is_error = clean_tool_result_content(raw)
            if cleaned != raw:
                shadow[key] = cleaned
                changed += 1
            if is_error and not shadow.get("is_error"):
                shadow["is_error"] = True
                changed += 1
    return changed


def clean_any_string(value: Any) -> tuple[Any, int]:
    if isinstance(value, str):
        cleaned = clean_text(value)
        return cleaned, 1 if cleaned != value else 0
    if isinstance(value, list):
        changed = 0
        items = []
        for item in value:
            new_item, count = clean_any_string(item)
            changed += count
            items.append(new_item)
        return items, changed
    if isinstance(value, dict):
        changed = 0
        obj = {}
        for key, item in value.items():
            new_item, count = clean_any_string(item)
            changed += count
            obj[key] = new_item
        return obj, changed
    return value, 0


def should_drop_text(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    return any(stripped.startswith(prefix) for prefix in DROP_TEXT_PREFIXES)


def message_text(record: dict[str, Any]) -> str | None:
    msg = record.get("message")
    if not isinstance(msg, dict):
        return None
    content = msg.get("content")
    if record.get("type") == "user" and isinstance(content, str):
        return content
    if record.get("type") == "assistant" and isinstance(content, list) and len(content) == 1:
        item = content[0]
        if isinstance(item, dict) and item.get("type") == "text":
            return item.get("text", "")
    return None


def set_message_text(record: dict[str, Any], text: str) -> None:
    if record.get("type") == "user":
        record.setdefault("message", {})["content"] = text
    elif record.get("type") == "assistant":
        record.setdefault("message", {})["content"] = [{"type": "text", "text": text}]


def title_from_text(text: str) -> str:
    text = re.sub(r"Referenced files:\n(?:- .+\n?)+", "", text, flags=re.S).strip()
    text = re.sub(r"Image attachment from original Codex turn was not migrated\.?", "", text)
    text = re.sub(r"Imported transcript note: truncated \d+ characters from this record\.?", "", text)
    text = re.sub(r"\]\]\s*</image>", "", text)
    text = text.replace("</image>", "")
    text = re.sub(r"\s+", " ", text)
    text = text.strip(" \n\r\t#：:，,。.")
    if not text:
        return "历史会话"
    return text[:80]


def is_import_intro(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith("Imported from Codex") or "Codex thread id:" in stripped[:500]


def first_real_user_text(records: list[dict[str, Any]]) -> str:
    for record in records:
        if record.get("type") != "user":
            continue
        content = record.get("message", {}).get("content")
        if isinstance(content, str) and content.strip():
            text = content.strip()
            if is_import_intro(text):
                continue
            return text
    return ""


def duplicate_title_suffixes(threads: list[dict[str, Any]]) -> dict[str, str]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for thread in threads:
        key = (thread["target_slug"], normalize_title_text(thread.get("title"), limit=500))
        grouped.setdefault(key, []).append(thread)

    suffixes: dict[str, str] = {}
    for items in grouped.values():
        if len(items) <= 1:
            continue
        for thread in sorted(items, key=lambda t: (t.get("updated_at") or 0, t["session_id"]), reverse=True):
            updated = thread.get("updated_at")
            date_text = ""
            if isinstance(updated, (int, float)) and updated > 0:
                try:
                    date_text = dt.datetime.fromtimestamp(updated, dt.timezone.utc).strftime("%Y-%m-%d")
                except (OverflowError, OSError, ValueError):
                    date_text = ""
            short_id = thread["session_id"].split("-")[0]
            suffixes[thread["session_id"]] = f" ({date_text} {short_id})" if date_text else f" ({short_id})"
    return suffixes


def build_display_titles(threads: list[dict[str, Any]]) -> dict[str, str]:
    overrides: dict[str, str] = {}
    if TITLE_OVERRIDES.exists():
        try:
            raw = json.loads(TITLE_OVERRIDES.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                overrides = {str(key): str(value) for key, value in raw.items() if isinstance(value, str) and value.strip()}
        except json.JSONDecodeError:
            overrides = {}

    suffixes = duplicate_title_suffixes(threads)
    titles: dict[str, str] = {}
    for thread in threads:
        override = overrides.get(thread["session_id"])
        if override:
            titles[thread["session_id"]] = normalize_project_title_prefix(thread, override)
            continue
        base = display_title_for_thread(thread)
        suffix = suffixes.get(thread["session_id"], "")
        titles[thread["session_id"]] = normalize_project_title_prefix(thread, (base[: max(1, 180 - len(suffix))] + suffix).strip())
    return titles


def normalize_project_title_prefix(thread: dict[str, Any], title: str) -> str:
    return title


def rebuild_parent_chain(records: list[dict[str, Any]]) -> None:
    parent = None
    default_cwd = next((r.get("cwd") for r in records if r.get("cwd")), "")
    default_ts = next((r.get("timestamp") for r in records if r.get("timestamp")), "")
    for index, record in enumerate(records):
        if not record.get("uuid"):
            record["uuid"] = str(uuid.uuid5(IMPORT_NAMESPACE, f"polish:{record.get('sessionId', '')}:{index}:{record.get('type', '')}"))
        if not record.get("cwd"):
            record["cwd"] = default_cwd
        if not record.get("timestamp"):
            record["timestamp"] = default_ts
        if record.get("type") in {"ai-title", "queue-operation"}:
            continue
        if record.get("type") in {"user", "assistant", "attachment"}:
            record["parentUuid"] = parent
            parent = record.get("uuid")


def polish_records(records: list[dict[str, Any]], display_title: str) -> tuple[list[dict[str, Any]], str, str, dict[str, int]]:
    stats = {
        "dropped": 0,
        "cleaned": 0,
        "deduped_user": 0,
        "title_updated": 0,
        "recursive_cleaned": 0,
        "patch_result_tool_result": 0,
        "tool_result_cleaned": 0,
    }
    polished: list[dict[str, Any]] = []
    last_user_text = None
    pending_tool_use: dict[str, str] | None = None

    for record in records:
        text = message_text(record)
        if text is not None:
            cleaned = clean_text(text)
            if should_drop_text(cleaned):
                stats["dropped"] += 1
                continue
            if record.get("type") == "assistant" and cleaned.strip().startswith("Patch apply result") and pending_tool_use:
                summary, is_error = summarize_patch_result(cleaned)
                set_user_tool_result(
                    record,
                    pending_tool_use["tool_use_id"],
                    summary,
                    pending_tool_use.get("assistant_uuid"),
                    is_error,
                )
                stats["patch_result_tool_result"] += 1
                pending_tool_use = None
                record, count = clean_any_string(record)
                stats["recursive_cleaned"] += count
                stats["tool_result_cleaned"] += clean_tool_results(record)
                polished.append(record)
                continue
            if record.get("type") == "user" and isinstance(record.get("message", {}).get("content"), str):
                norm = re.sub(r"\s+", " ", cleaned)
                if norm and norm == last_user_text:
                    stats["deduped_user"] += 1
                    continue
                last_user_text = norm
            if cleaned != text:
                set_message_text(record, cleaned)
                stats["cleaned"] += 1
        record, count = clean_any_string(record)
        stats["recursive_cleaned"] += count
        stats["tool_result_cleaned"] += clean_tool_results(record)
        polished.append(record)
        tool_use = single_tool_use(record)
        if tool_use:
            pending_tool_use = tool_use
        elif record.get("type") == "user":
            msg = record.get("message", {})
            content = msg.get("content") if isinstance(msg, dict) else None
            if isinstance(content, list) and any(isinstance(item, dict) and item.get("type") == "tool_result" for item in content):
                pending_tool_use = None

    initial = first_real_user_text(polished)
    titled = display_title

    has_title = False
    for record in polished:
        if record.get("type") == "ai-title":
            record["aiTitle"] = titled
            has_title = True
            stats["title_updated"] += 1
    if not has_title and polished:
        first = polished[0]
        polished.insert(
            0,
            {
                "type": "ai-title",
                "aiTitle": titled,
                "sessionId": first.get("sessionId"),
                "uuid": first.get("uuid"),
                "timestamp": first.get("timestamp"),
                "cwd": first.get("cwd"),
            },
        )
        stats["title_updated"] += 1

    rebuild_parent_chain(polished)
    return polished, titled, initial, stats


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    return records


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")


def update_metadata(thread: dict[str, Any], title: str, initial: str) -> bool:
    session_dir = discover_claude_3p_session_dir()
    if session_dir is None:
        return False
    path = session_dir / f"{local_session_id_for_cli_session(thread['session_id'])}.json"
    if not path.exists():
        return False
    obj = json.loads(path.read_text(encoding="utf-8"))
    project_label = thread.get("target_label") or PROJECT_LABELS.get(thread["target_slug"]) or thread["target_slug"]
    obj["title"] = title
    obj["initialMessage"] = initial[:2000]
    obj["cwd"] = thread["target_cwd"]
    obj["originCwd"] = thread["target_cwd"]
    obj["userSelectedFolders"] = [ui_path(thread["target_cwd"])]
    obj["projectName"] = project_label
    obj["projectPath"] = thread["target_cwd"]
    obj["workspaceRoot"] = thread["target_cwd"]
    obj.setdefault("codexImport", {})
    obj["codexImport"].update(
        {
            "threadId": thread["id"],
            "projectSlug": thread["target_slug"],
            "projectName": project_label,
            "cwd": thread["target_cwd"],
        }
    )
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    return True


def repair_all_target_metadata() -> int:
    session_dir = discover_claude_3p_session_dir()
    if session_dir is None:
        return 0
    targets_by_cwd = {normalize_path(target["cwd"]): target for target in TARGETS}
    changed = 0
    for path in session_dir.glob("local_*.json"):
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        cwd = obj.get("cwd") or obj.get("originCwd")
        target = targets_by_cwd.get(normalize_path(cwd))
        if not target:
            continue
        label = target.get("label") or obj.get("projectName") or "Claude Code"
        desired = {
            "cwd": target["cwd"],
            "originCwd": target["cwd"],
            "userSelectedFolders": [ui_path(target["cwd"])],
            "projectName": label,
            "projectPath": target["cwd"],
            "workspaceRoot": target["cwd"],
        }
        updated = False
        for key, value in desired.items():
            if obj.get(key) != value:
                obj[key] = value
                updated = True
        if updated:
            path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
            changed += 1
    return changed


def residual_counts(threads: list[dict[str, Any]]) -> dict[str, int]:
    patterns = {
        "environment_context": "<environment_context>",
        "oai_mem_citation": "<oai-mem-citation>",
        "codex_internal_context": "<codex_internal_context",
        "apply_patch_shell_warning": "Warning: apply_patch was requested via shell.",
        "codex_git_directive": "::git-",
        "imported_context_event": "Imported context event:",
        "compacted_context": "Compacted context",
        "thread_rolled_back": "thread_rolled_back",
        "turn_aborted": "turn_aborted",
        "agents_context": "# AGENTS.md instructions",
        "files_wrapper": "# Files mentioned by the user:",
        "codex_import_title": "Codex import:",
        "patch_apply_result": "Patch apply result",
        "imported_codex_shell": "Imported Codex shell command",
        "imported_codex_patch": "Imported Codex patch",
        "base_instructions": "base_instructions",
    }
    counts = {k: 0 for k in patterns}
    for thread in threads:
        text = Path(thread["dest"]).read_text(encoding="utf-8")
        for key, pattern in patterns.items():
            counts[key] += text.count(pattern)
    return counts


def main() -> int:
    threads = [thread for thread in get_threads() if Path(thread["dest"]).exists()]
    display_titles = build_display_titles(threads)
    backup = ensure_backup()
    totals: dict[str, int] = {"metadata_updated": 0, "target_metadata_repaired": 0, "files": 0}
    for thread in threads:
        path = Path(thread["dest"])
        records = read_jsonl(path)
        polished, title, initial, stats = polish_records(records, display_titles[thread["session_id"]])
        write_jsonl(path, polished)
        if update_metadata(thread, title, initial):
            totals["metadata_updated"] += 1
        totals["files"] += 1
        for key, value in stats.items():
            totals[key] = totals.get(key, 0) + value
    totals["target_metadata_repaired"] = repair_all_target_metadata()

    report = {
        "backup": str(backup),
        "totals": totals,
        "residual_counts": residual_counts(threads),
        "validation": validate_imported(threads),
        "desktop_validation": validate_desktop_sessions(threads),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["validation"].get("ok") or not report["desktop_validation"].get("ok"):
        return 2
    if any(report["residual_counts"].values()):
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
