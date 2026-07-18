#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python version guard
    tomllib = None


SEVERITY_RANK = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
SECRET_KEY = re.compile(r"(?i)(api[_-]?key|token|secret|password|credential|cookie)")
SECRET_VALUE_PATTERNS = (
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_.-]{16,}"),
    re.compile(r"-----BEGIN\s+(?:RSA\s+|EC\s+|OPENSSH\s+)?PRIVATE\s+KEY-----"),
)
SHELL_COMMANDS = {"bash", "cmd", "cmd.exe", "fish", "powershell", "powershell.exe", "pwsh", "pwsh.exe", "sh", "zsh"}
SHELL_FLAGS = {"-c", "/c", "-command", "-encodedcommand", "-enc"}
PACKAGE_RUNNERS = {"npx", "npx.cmd", "uvx"}
LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}


def is_placeholder(value: str) -> bool:
    lowered = value.lower().strip()
    return (
        not lowered
        or "${" in value
        or re.fullmatch(r"%[A-Za-z_][A-Za-z0-9_]*%", value.strip()) is not None
        or re.fullmatch(r"\$[A-Za-z_][A-Za-z0-9_]*", value.strip()) is not None
        or "process.env." in lowered
        or "os.environ" in lowered
        or any(word in lowered for word in ("example", "placeholder", "your_", "your-", "changeme", "redacted"))
        or (value.startswith("<") and value.endswith(">"))
    )


def load_config(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    text = data.decode("utf-8-sig")
    if path.suffix.lower() == ".toml":
        if tomllib is None:
            raise RuntimeError("Python 3.11+ is required to audit TOML files")
        parsed = tomllib.loads(text)
    else:
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            if tomllib is None:
                raise
            parsed = tomllib.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("configuration root must be an object/table")
    return parsed


def extract_servers(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    candidates: Any = config.get("mcpServers") or config.get("mcp_servers")
    if candidates is None and isinstance(config.get("mcp"), dict):
        candidates = config["mcp"].get("servers")
    if not isinstance(candidates, dict):
        raise ValueError("no supported MCP server table found")
    return {str(name): value for name, value in candidates.items() if isinstance(value, dict)}


def walk_strings(value: Any, location: str = "$"):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk_strings(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_strings(child, f"{location}[{index}]")
    elif isinstance(value, str):
        yield location, value


def finding(severity: str, code: str, server: str, location: str, message: str, fix: str) -> dict[str, str]:
    return {
        "severity": severity,
        "code": code,
        "server": server,
        "location": location,
        "message": message,
        "fix": fix,
    }


def secret_findings(server: str, config: dict[str, Any]) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for location, value in walk_strings(config, f"$.mcp_servers.{server}"):
        key_name = location.rsplit(".", 1)[-1]
        if SECRET_KEY.search(key_name) and len(value) >= 8 and not is_placeholder(value):
            results.append(finding("critical", "hardcoded-secret", server, location, "Credential-like value is stored directly in configuration; value redacted.", "Reference an environment variable or supported secret store."))
            continue
        if not is_placeholder(value) and any(pattern.search(value) for pattern in SECRET_VALUE_PATTERNS):
            results.append(finding("critical", "secret-pattern", server, location, "Secret-like token or private key pattern detected; value redacted.", "Rotate the credential if real and replace it with a secret reference."))
        parsed = urlparse(value)
        if parsed.scheme and parsed.username and parsed.password and not is_placeholder(parsed.password):
            results.append(finding("critical", "url-credentials", server, location, "URL contains embedded username and password; values redacted.", "Use separate environment-backed authentication settings."))
    return results


def command_basename(command: str) -> str:
    return command.replace("\\", "/").rsplit("/", 1)[-1].lower()


def launcher_findings(server: str, config: dict[str, Any]) -> list[dict[str, str]]:
    command = str(config.get("command") or "")
    args = [str(value) for value in config.get("args", []) if isinstance(value, (str, int, float))]
    lowered_args = {value.lower() for value in args}
    base = command_basename(command)
    results: list[dict[str, str]] = []
    if base in SHELL_COMMANDS and lowered_args.intersection(SHELL_FLAGS):
        results.append(finding("high", "shell-launcher", server, f"$.mcp_servers.{server}.command", "MCP server is launched through a command shell, which expands the injection surface.", "Invoke the executable directly with an argument array whenever possible."))
    if base in {"eval", "eval.exe"}:
        results.append(finding("high", "eval-launcher", server, f"$.mcp_servers.{server}.command", "Configuration launches eval directly.", "Replace eval with a direct executable invocation."))
    return results


def package_target(command: str, args: list[str]) -> tuple[str | None, str]:
    base = command_basename(command)
    lowered = [value.lower() for value in args]
    mode = base
    start = 0
    if base in {"pnpm", "pnpm.cmd"} and lowered and lowered[0] == "dlx":
        mode = "pnpm-dlx"
        start = 1
    elif base in {"pipx", "pipx.exe"} and lowered and lowered[0] == "run":
        mode = "pipx-run"
        start = 1
    elif base not in PACKAGE_RUNNERS:
        return None, mode
    for value in args[start:]:
        if value.startswith("-"):
            continue
        return value, mode
    return None, mode


def is_pinned_package(target: str, mode: str) -> bool:
    if target.startswith((".", "/", "\\", "git+", "http://", "https://")):
        return True
    if mode in {"uvx", "pipx-run"}:
        return "==" in target or "@" in target
    if target.startswith("@"):
        return target.count("@") >= 2 and not target.lower().endswith("@latest")
    return "@" in target and not target.lower().endswith("@latest")


def package_findings(server: str, config: dict[str, Any]) -> list[dict[str, str]]:
    command = str(config.get("command") or "")
    args = [str(value) for value in config.get("args", []) if isinstance(value, (str, int, float))]
    target, mode = package_target(command, args)
    if target and not is_pinned_package(target, mode):
        return [finding("medium", "unpinned-package", server, f"$.mcp_servers.{server}.args", "Package runner target is not pinned to an exact version.", "Pin the package to a reviewed exact version or immutable source revision.")]
    return []


def remote_findings(server: str, config: dict[str, Any]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    url = config.get("url")
    findings: list[dict[str, str]] = []
    assumptions: list[dict[str, str]] = []
    if isinstance(url, str):
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme == "http" and host not in LOCAL_HOSTS:
            findings.append(finding("high", "insecure-remote-url", server, f"$.mcp_servers.{server}.url", "Remote MCP endpoint uses plain HTTP.", "Use HTTPS or document a trusted private transport boundary."))
        if host and host not in LOCAL_HOSTS:
            assumptions.append({"server": server, "type": "external-host", "name": host})
    env = config.get("env")
    if isinstance(env, dict):
        for key, value in env.items():
            if isinstance(value, str) and is_placeholder(value):
                assumptions.append({"server": server, "type": "environment-variable", "name": str(key)})
    return findings, assumptions


def audit_config(config: dict[str, Any], approved: set[str] | None = None) -> dict[str, Any]:
    servers = extract_servers(config)
    findings: list[dict[str, str]] = []
    assumptions: list[dict[str, str]] = []
    for name, server_config in sorted(servers.items()):
        findings.extend(secret_findings(name, server_config))
        findings.extend(launcher_findings(name, server_config))
        findings.extend(package_findings(name, server_config))
        remote, server_assumptions = remote_findings(name, server_config)
        findings.extend(remote)
        assumptions.extend(server_assumptions)
        if approved is not None and name not in approved:
            findings.append(finding("medium", "unapproved-server", name, f"$.mcp_servers.{name}", "Server name is not present in the supplied approved list.", "Review provenance, then add the exact server name to the governed allowlist if accepted."))
    by_severity = {severity: 0 for severity in SEVERITY_RANK}
    for item in findings:
        by_severity[item["severity"]] += 1
    return {
        "servers": sorted(servers),
        "findings": findings,
        "assumptions": assumptions,
        "summary": {"serverCount": len(servers), "findingCount": len(findings), "bySeverity": by_severity},
    }


def render_text(path: Path, result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [f"MCP security audit: {path}", f"Servers: {summary['serverCount']}  Findings: {summary['findingCount']}"]
    for item in result["findings"]:
        lines.append(f"[{item['severity'].upper()}] {item['server']} {item['code']} at {item['location']}: {item['message']}")
        lines.append(f"  Fix: {item['fix']}")
    if result["assumptions"]:
        lines.append("Runtime assumptions:")
        for item in result["assumptions"]:
            lines.append(f"- {item['server']}: {item['type']} {item['name']}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only MCP configuration security audit.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--approved", action="append", default=None, help="Approved server name; repeat for multiple names.")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--fail-on", choices=tuple(SEVERITY_RANK), default="high")
    args = parser.parse_args()
    try:
        config = load_config(args.path)
        result = audit_config(config, set(args.approved) if args.approved is not None else None)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"audit failed: {exc}", file=sys.stderr)
        return 2
    result["file"] = str(args.path)
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_text(args.path, result))
    threshold = SEVERITY_RANK[args.fail_on]
    return 1 if any(SEVERITY_RANK[item["severity"]] >= threshold for item in result["findings"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
