#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.1"
REPO_URL = "https://github.com/2508756189/state-of-art-skills"
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_.-]{10,}"),
    re.compile(r"ctp_[A-Za-z0-9_.-]{10,}"),
    re.compile(r"(?i)(api[_-]?key|token|cookie|secret)\s*[:=]\s*[A-Za-z0-9_.-]{12,}"),
]
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".zip"}
EXCLUDED_DIRECTORY_NAMES = {
    ".git",
    ".in_use",
    ".venv",
    "__pycache__",
    "backups",
    "node_modules",
    "venv",
}
EXCLUDED_FILE_NAMES = {".DS_Store", "Thumbs.db"}
EXCLUDED_FILE_SUFFIXES = {".7z", ".bak", ".log", ".pyc", ".pyo", ".tmp", ".zip"}
ALLOWED_FRONTMATTER_KEYS = {"name", "description", "license", "allowed-tools", "metadata"}


class MarketError(RuntimeError):
    pass


def is_placeholder_secret(value: str) -> bool:
    lowered = value.lower()
    return (
        "process.env." in value
        or "os.environ" in value
        or "your_" in lowered
        or "example" in lowered
        or "placeholder" in lowered
        or value.startswith("<")
    )


def parse_frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not match:
        raise MarketError(f"{path} missing YAML frontmatter")
    data: dict[str, Any] = {}
    current_key: str | None = None
    for raw_line in match.group(1).splitlines():
        if not raw_line.strip():
            continue
        if raw_line.startswith("  ") and current_key:
            data.setdefault(current_key, [])
            if isinstance(data[current_key], list):
                data[current_key].append(raw_line.strip().lstrip("- "))
            continue
        if ":" not in raw_line:
            continue
        key, value = raw_line.split(":", 1)
        current_key = key.strip()
        value = value.strip()
        if value == "[]":
            data[current_key] = []
        elif value:
            data[current_key] = value.strip('"').strip("'")
        else:
            data[current_key] = []
    if not data.get("name") or not data.get("description"):
        raise MarketError(f"{path} frontmatter must include name and description")
    unexpected = sorted(set(data) - ALLOWED_FRONTMATTER_KEYS)
    if unexpected:
        raise MarketError(f"{path} frontmatter has unsupported keys: {', '.join(unexpected)}")
    return data


def skill_markdown_body(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n.*?\n---\n?", text, re.S)
    body = text[match.end():] if match else text
    return body.replace("\r\n", "\n").replace("\r", "\n").lstrip()


def load_categories(root: Path) -> dict[str, Any]:
    path = root / "market" / "categories.json"
    if not path.exists():
        return {"categories": [], "skills": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def should_package_path(path: Path, skill_dir: Path) -> bool:
    relative = path.relative_to(skill_dir)
    if any(part in EXCLUDED_DIRECTORY_NAMES for part in relative.parts[:-1]):
        return False
    if path.name in EXCLUDED_FILE_NAMES or path.suffix.lower() in EXCLUDED_FILE_SUFFIXES:
        return False
    if path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example"):
        return False
    if path.name.endswith(".local.md"):
        return False
    return True


def skill_runtime_files(skill_dir: Path) -> list[Path]:
    return [
        path
        for path in sorted(skill_dir.rglob("*"))
        if path.is_file() and should_package_path(path, skill_dir)
    ]


def scan_for_secrets(skill_dir: Path) -> None:
    for path in skill_runtime_files(skill_dir):
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            for pattern in SECRET_PATTERNS:
                match = pattern.search(line)
                if match and not is_placeholder_secret(line[match.start() :].strip()):
                    raise MarketError(f"{path} contains secret-like content")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def archive_file_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    if path.suffix.lower() in BINARY_SUFFIXES or b"\0" in data:
        return data
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def zip_skill(root: Path, skill_dir: Path, dist_dir: Path) -> tuple[Path, str, int]:
    archive = dist_dir / f"{skill_dir.name}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in skill_runtime_files(skill_dir):
            info = zipfile.ZipInfo(str(path.relative_to(root)).replace("\\", "/"))
            info.date_time = (2026, 1, 1, 0, 0, 0)
            info.create_system = 0
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, archive_file_bytes(path))
    return archive, sha256_file(archive), archive.stat().st_size


def expected_zip_contents(root: Path, skill_dir: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)).replace("\\", "/"): archive_file_bytes(path)
        for path in skill_runtime_files(skill_dir)
    }


def validate_existing_artifacts(root: Path) -> None:
    registry_path = root / "market" / "index.json"
    if not registry_path.exists():
        raise MarketError(f"registry not found: {registry_path}")
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    for item in registry.get("skills", []):
        if not isinstance(item, dict):
            raise MarketError("registry contains a non-object skill item")
        skill_id = str(item.get("id") or "")
        skill_dir = root / "skills" / skill_id
        if not skill_dir.exists():
            raise MarketError(f"registry skill {skill_id!r} has no source directory")
        archive = item.get("archive") if isinstance(item.get("archive"), dict) else {}
        archive_path = root / str(archive.get("path") or "")
        if not archive_path.exists():
            raise MarketError(f"{skill_id} archive not found: {archive_path}")
        checksum = str(archive.get("sha256") or "")
        size = int(archive.get("size") or 0)
        if checksum != sha256_file(archive_path):
            raise MarketError(f"{skill_id} archive checksum is stale")
        if size != archive_path.stat().st_size:
            raise MarketError(f"{skill_id} archive size is stale")

        expected = expected_zip_contents(root, skill_dir)
        with zipfile.ZipFile(archive_path) as zf:
            actual_names = sorted(info.filename for info in zf.infolist() if not info.is_dir())
            if actual_names != sorted(expected):
                raise MarketError(f"{skill_id} archive contents are stale")
            for name, expected_bytes in expected.items():
                if zf.read(name) != expected_bytes:
                    raise MarketError(f"{skill_id} archive file is stale: {name}")

        detail = item.get("detail") if isinstance(item.get("detail"), dict) else {}
        markdown_path = str(detail.get("markdownPath") or "")
        if markdown_path:
            detail_path = root / "market" / markdown_path
            if not detail_path.exists():
                raise MarketError(f"{skill_id} detail markdown not found: {detail_path}")
            expected_detail = skill_markdown_body(skill_dir / "SKILL.md")
            if detail_path.read_text(encoding="utf-8") != expected_detail:
                raise MarketError(f"{skill_id} detail markdown is stale")


def default_install_targets(skill_id: str, runtime: list[str]) -> dict[str, str]:
    targets: dict[str, str] = {}
    if "codex" in runtime or "portable" in runtime:
        targets["codex"] = f"~/.codex/skills/{skill_id}"
    if "claude" in runtime or "portable" in runtime:
        targets["claude"] = f"~/.claude/skills/{skill_id}"
    if "portable" in runtime:
        targets["portable"] = f"~/.agents/skills/{skill_id}"
    return targets


def normalize_list(value: Any, fallback: list[str]) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return fallback


def build_detail(skill_id: str, meta: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    detail = override.get("detail") if isinstance(override.get("detail"), dict) else {}
    return {
        "summary": str(detail.get("summary") or meta.get("description") or ""),
        "useCases": normalize_list(detail.get("useCases"), []),
        "capabilities": normalize_list(detail.get("capabilities"), []),
        "requirements": normalize_list(detail.get("requirements"), []),
        "permissions": normalize_list(detail.get("permissions"), []),
        "markdownPath": f"details/{skill_id}.md",
    }


def build_market(root: Path, write: bool) -> dict[str, Any]:
    skills_root = root / "skills"
    if not skills_root.exists():
        raise MarketError(f"skills directory not found: {skills_root}")

    config = load_categories(root)
    overrides = config.get("skills", {}) if isinstance(config.get("skills"), dict) else {}
    categories = config.get("categories", []) if isinstance(config.get("categories"), list) else []
    category_ids = {str(item.get("id")) for item in categories if isinstance(item, dict)}

    dist_dir = root / "dist" / "skills"
    detail_dir = root / "market" / "details"
    if write:
        dist_dir.mkdir(parents=True, exist_ok=True)
        detail_dir.mkdir(parents=True, exist_ok=True)

    seen_names: dict[str, Path] = {}
    items: list[dict[str, Any]] = []
    for skill_dir in sorted(path for path in skills_root.iterdir() if path.is_dir()):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            raise MarketError(f"{skill_dir} missing SKILL.md")
        meta = parse_frontmatter(skill_md)
        name = str(meta["name"])
        if name in seen_names:
            raise MarketError(f"Duplicate skill name: {name} in {skill_md} and {seen_names[name]}")
        seen_names[name] = skill_md
        scan_for_secrets(skill_dir)

        override = overrides.get(skill_dir.name, {})
        if not isinstance(override, dict):
            override = {}
        runtime = normalize_list(override.get("runtime"), ["portable"])
        category = str(override.get("category") or "workflow")
        if category_ids and category not in category_ids:
            raise MarketError(f"{skill_dir.name} category {category!r} not declared in categories.json")
        tags = normalize_list(override.get("tags"), [])
        risk_level = str(override.get("riskLevel") or "low")
        source = str(override.get("source") or meta.get("source") or REPO_URL)
        version = str(override.get("version") or meta.get("version") or "0.1.0")
        license_value = str(override.get("license") or meta.get("license") or "review-required")
        detail = build_detail(skill_dir.name, meta, override)

        archive_path: Path | None = None
        checksum = ""
        size = 0
        if write:
            archive_path, checksum, size = zip_skill(root, skill_dir, dist_dir)
            (detail_dir / f"{skill_dir.name}.md").write_text(
                skill_markdown_body(skill_md),
                encoding="utf-8",
            )

        item = {
            "id": skill_dir.name,
            "name": name,
            "description": str(meta["description"]),
            "category": category,
            "tags": tags,
            "runtime": runtime,
            "installTargets": default_install_targets(skill_dir.name, runtime),
            "version": version,
            "license": license_value,
            "source": source,
            "riskLevel": risk_level,
            "path": f"skills/{skill_dir.name}",
            "detail": detail,
            "archive": {
                "path": str(archive_path.relative_to(root)).replace("\\", "/") if archive_path else f"dist/skills/{skill_dir.name}.zip",
                "sha256": checksum,
                "size": size,
            },
        }
        items.append(item)

    registry = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "repository": REPO_URL,
        "categories": categories,
        "skills": items,
    }
    if write:
        market_dir = root / "market"
        market_dir.mkdir(parents=True, exist_ok=True)
        (market_dir / "index.json").write_text(
            json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return registry


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and validate the TokenPort skill market registry.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true", help="Validate only; do not write market/index.json or zip files.")
    args = parser.parse_args()
    try:
        registry = build_market(args.root.resolve(), write=not args.check)
        if args.check:
            validate_existing_artifacts(args.root.resolve())
    except MarketError as exc:
        print(f"market validation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"skills": len(registry["skills"]), "write": not args.check}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
