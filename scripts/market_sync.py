#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any


RISK_RANK = {"low": 0, "medium": 1, "high": 2}


def load_registry(source: str) -> dict[str, Any]:
    if source.startswith("http://") or source.startswith("https://"):
        with urllib.request.urlopen(source, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    return json.loads(Path(source).read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def skills_by_id(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item["id"]): item for item in registry.get("skills", [])}


def archive_error(root: Path, item: dict[str, Any]) -> str | None:
    archive = item.get("archive") or {}
    archive_path = archive.get("path")
    expected = archive.get("sha256")
    if not archive_path or not expected:
        return "archive path or sha256 missing"
    path = root / str(archive_path)
    if not path.exists():
        return f"archive missing: {archive_path}"
    actual = sha256_file(path)
    if actual != expected:
        return f"sha256 mismatch: expected {expected}, got {actual}"
    return None


def risk_rank(value: str) -> int:
    return RISK_RANK.get(str(value), -1)


def diff_registries(
    local: dict[str, Any],
    remote: dict[str, Any],
    *,
    root: Path | None = None,
    verify_archives: bool = False,
) -> list[dict[str, Any]]:
    local_items = skills_by_id(local)
    results: list[dict[str, Any]] = []

    for remote_item in sorted(remote.get("skills", []), key=lambda item: str(item.get("id", ""))):
        skill_id = str(remote_item["id"])
        local_item = local_items.get(skill_id)

        if verify_archives and root is not None:
            error = archive_error(root, remote_item)
            if error:
                results.append(
                    {
                        "id": skill_id,
                        "status": "checksum_failed",
                        "localVersion": local_item.get("version") if local_item else None,
                        "remoteVersion": remote_item.get("version"),
                        "reason": error,
                    }
                )
                continue

        if local_item is None:
            status = "new"
            reason = "not installed in local registry"
        elif risk_rank(remote_item.get("riskLevel", "")) > risk_rank(local_item.get("riskLevel", "")):
            status = "risk_increased"
            reason = f"risk changed from {local_item.get('riskLevel')} to {remote_item.get('riskLevel')}"
        elif (
            remote_item.get("version") != local_item.get("version")
            or (remote_item.get("archive") or {}).get("sha256") != (local_item.get("archive") or {}).get("sha256")
        ):
            status = "upgradable"
            reason = "version or archive checksum differs"
        else:
            status = "current"
            reason = "local registry matches remote item"

        results.append(
            {
                "id": skill_id,
                "status": status,
                "localVersion": local_item.get("version") if local_item else None,
                "remoteVersion": remote_item.get("version"),
                "localRisk": local_item.get("riskLevel") if local_item else None,
                "remoteRisk": remote_item.get("riskLevel"),
                "reason": reason,
            }
        )

    return results


def summarize(results: list[dict[str, Any]]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for item in results:
        status = str(item["status"])
        summary[status] = summary.get(status, 0) + 1
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare TokenPort Skill Market registries.")
    parser.add_argument("--local", required=True, help="Local market/index.json path")
    parser.add_argument("--remote", required=True, help="Remote or local market/index.json path")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Root used to verify archive paths")
    parser.add_argument("--verify-archives", action="store_true", help="Verify remote archive SHA256 values")
    parser.add_argument("--output", choices=["json", "summary"], default="summary")
    args = parser.parse_args()

    try:
        local = load_registry(args.local)
        remote = load_registry(args.remote)
        results = diff_registries(local, remote, root=args.root, verify_archives=args.verify_archives)
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
        print(f"market sync diff failed: {exc}", file=sys.stderr)
        return 1

    payload = {"summary": summarize(results), "items": results}
    if args.output == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload["summary"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
