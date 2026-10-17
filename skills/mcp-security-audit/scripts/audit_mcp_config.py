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
NPM_LAUNCHERS = {"npx", "npx.cmd", "bunx", "bunx.cmd"}
DLX_LAUNCHERS = {"pnpm", "pnpm.cmd", "yarn", "yarn.cmd", "bun", "bun.cmd"}
UV_LAUNCHERS = {"uvx", "uvx.exe"}
EXACT_SEMVER = re.compile(r"^v?\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
MUTABLE_TAG = re.compile(r"^[A-Za-z][A-Za-z0-9._-]*$")
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


def split_package_spec(spec: str) -> tuple[str, str | None]:
    spec = spec.strip()
    if "==" in spec:
        package, version = spec.split("==", 1)
        return package, f"=={version}"
    if spec.startswith("@"):
        slash = spec.find("/")
        at = spec.rfind("@")
        if slash >= 0 and at > slash:
            return spec[:at], spec[at + 1 :] or None
        return spec, None
    if "@" in spec:
        package, version = spec.rsplit("@", 1)
        return package, version or None
    return spec, None


def is_exact_version(version: str) -> bool:
    candidate = version.strip()
    if candidate.startswith("=="):
        candidate = candidate[2:]
    return bool(EXACT_SEMVER.fullmatch(candidate))


def package_targets(command: str, args: list[str]) -> tuple[list[str] | None, str]:
    """Return package selectors and the launcher mode; an empty mode means "not a package runner".

    A ``None`` selector list with a non-empty mode means the launcher is recognised but the
    selectors cannot be classified statically. That is reported for manual review instead of
    being treated as clean.
    """
    base = command_basename(command)
    lowered = [value.lower() for value in args]
    if base in {"npm", "npm.cmd"}:
        if not lowered or lowered[0] not in {"exec", "x"}:
            return None, ""
        mode, rest = "npm-exec", args[1:]
    elif base in DLX_LAUNCHERS:
        if not lowered or lowered[0] not in {"dlx", "x"}:
            return None, ""
        mode, rest = "dlx", args[1:]
    elif base in {"pipx", "pipx.exe"}:
        if not lowered or lowered[0] != "run":
            return None, ""
        mode, rest = "pipx-run", args[1:]
    elif base in NPM_LAUNCHERS:
        mode, rest = "npm-launcher", args
    elif base in UV_LAUNCHERS:
        mode, rest = "uvx", args
    else:
        return None, ""

    selectors: list[str] = []
    index = 0
    while index < len(rest):
        value = rest[index]
        if value in {"-p", "--package", "--from"}:
            index += 1
            if index >= len(rest) or not rest[index] or rest[index].startswith("-"):
                return None, mode
            selectors.append(rest[index])
        elif value.startswith(("--package=", "--from=")):
            selector = value.split("=", 1)[1]
            if not selector:
                return None, mode
            selectors.append(selector)
        elif value in {"-y", "--yes", "--no", "--quiet", "-q"}:
            pass
        elif value == "--":
            if selectors:
                return selectors, mode
            return ([rest[index + 1]] if index + 1 < len(rest) else None), mode
        elif value.startswith("-"):
            return None, mode
        else:
            return (selectors or [value]), mode
        index += 1
    return (selectors or None), mode


def package_findings(server: str, config: dict[str, Any]) -> list[dict[str, str]]:
    command = str(config.get("command") or "")
    args = [str(value) for value in config.get("args", []) if isinstance(value, (str, int, float))]
    targets, mode = package_targets(command, args)
    if not mode:
        return []
    if targets is None:
        return [finding("info", "package-selector-unclear", server, f"$.mcp_servers.{server}.args", "Package runner selector could not be classified statically.", "Review the launcher and selector as text; do not execute the configured command.")]
    results: list[dict[str, str]] = []
    for target in targets:
        if target.startswith((".", "/", "\\", "git+", "http://", "https://")):
            continue
        package, version = split_package_spec(target)
        if version is not None and is_exact_version(version):
            continue
        if version is None or MUTABLE_TAG.fullmatch(version.lstrip("=")):
            results.append(finding("medium", "mutable-package", server, f"$.mcp_servers.{server}.args", f"Package reference '{target}' can resolve to different code later.", f"Pin {package} to the exact version that was actually reviewed."))
        else:
            results.append(finding("low", "non-exact-package", server, f"$.mcp_servers.{server}.args", f"Package reference '{target}' is not an exact version.", f"Pin {package} to the exact version that was actually reviewed."))
    return results


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
