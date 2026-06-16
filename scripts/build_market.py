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


SCHEMA_VERSION = "1.0"
REPO_URL = "https://github.com/2508756189/state-of-art-skills"
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_.-]{10,}"),
    re.compile(r"ctp_[A-Za-z0-9_.-]{10,}"),
    re.compile(r"(?i)(api[_-]?key|token|cookie|secret)\s*[:=]\s*[A-Za-z0-9_.-]{12,}"),
]


class MarketError(RuntimeError):
    pass


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
    return data


def load_categories(root: Path) -> dict[str, Any]:
    path = root / "market" / "categories.json"
    if not path.exists():
        return {"categories": [], "skills": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def scan_for_secrets(skill_dir: Path) -> None:
    for path in skill_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                raise MarketError(f"{path} contains secret-like content")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def zip_skill(root: Path, skill_dir: Path, dist_dir: Path) -> tuple[Path, str, int]:
    archive = dist_dir / f"{skill_dir.name}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(skill_dir.rglob("*")):
            if path.is_file():
                info = zipfile.ZipInfo(str(path.relative_to(root)).replace("\\", "/"))
                info.date_time = (2026, 1, 1, 0, 0, 0)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                zf.writestr(info, path.read_bytes())
    return archive, sha256_file(archive), archive.stat().st_size


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


def build_market(root: Path, write: bool) -> dict[str, Any]:
    skills_root = root / "skills"
    if not skills_root.exists():
        raise MarketError(f"skills directory not found: {skills_root}")

    config = load_categories(root)
    overrides = config.get("skills", {}) if isinstance(config.get("skills"), dict) else {}
    categories = config.get("categories", []) if isinstance(config.get("categories"), list) else []
    category_ids = {str(item.get("id")) for item in categories if isinstance(item, dict)}

    dist_dir = root / "dist" / "skills"
    if write:
        dist_dir.mkdir(parents=True, exist_ok=True)

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

        archive_path: Path | None = None
        checksum = ""
        size = 0
        if write:
            archive_path, checksum, size = zip_skill(root, skill_dir, dist_dir)

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
            "archive": {
                "path": str(archive_path.relative_to(root)).replace("\\", "/") if archive_path else f"dist/skills/{skill_dir.name}.zip",
                "sha256": checksum,
                "size": size,
            },
        }
        items.append(item)

    existing_generated_at = None
    existing_index = root / "market" / "index.json"
    if existing_index.exists():
        try:
            existing_generated_at = json.loads(existing_index.read_text(encoding="utf-8")).get("generatedAt")
        except (OSError, json.JSONDecodeError):
            existing_generated_at = None

    registry = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": existing_generated_at
        or datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
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
    except MarketError as exc:
        print(f"market validation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"skills": len(registry["skills"]), "write": not args.check}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
