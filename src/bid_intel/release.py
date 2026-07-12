from __future__ import annotations

import json
import platform
import re
import sqlite3
from pathlib import Path
from typing import Any

from .config_validation import validate_config


REQUIRED_PATHS = (
    "README.md",
    "LICENSE",
    "CONTRIBUTING.md",
    "SECURITY.md",
    ".gitattributes",
    "pyproject.toml",
    "run.py",
    "bid-intel.cmd",
    "src/bid_intel/profiles.py",
    "src/bid_intel/dashboard.py",
    "src/bid_intel/connectors.py",
    "src/bid_intel/config_validation.py",
    "src/bid_intel/exports.py",
    "src/bid_intel/onboarding.py",
    "schemas/profile.schema.json",
    "schemas/sources.schema.json",
    "src/bid_intel/feed_connector.py",
    "samples/sources.rss.example.json",
    "docs/assets/dashboard-preview.png",
    "src/bid_intel/profiles/it-digital.json",
    "src/bid_intel/profiles/education.json",
    "scripts/daily.ps1",
    "scripts/weekly_intelligence.ps1",
    "scripts/install_task.ps1",
    "scripts/uninstall_task.ps1",
    "scripts/install_weekly_task.ps1",
    "scripts/uninstall_weekly_task.ps1",
    "docs/OPERATIONS.md",
    "docs/DATA_SOURCES.md",
    "docs/DATA_HANDLING.md",
    "docs/PROFILE_PACKS.md",
    ".github/workflows/tests.yml",
    ".github/workflows/pages.yml",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
    ".github/ISSUE_TEMPLATE/config.yml",
)


PUBLIC_TEXT_SUFFIXES = {".py", ".md", ".json", ".toml", ".yml", ".yaml", ".ps1", ".cmd", ".example", ".txt"}
PUBLIC_SCAN_EXCLUDED = {".git", "data", "reports", "__pycache__", ".pytest_cache", ".venv"}
LIVE_FEISHU_WEBHOOK = re.compile(r"https://open\.feishu\.cn/open-apis/bot/v2/hook/[A-Za-z0-9_-]{8,}")
PRIVATE_PUBLIC_TERMS = ("".join(chr(code) for code in (0x970D, 0x83B1, 0x6C83)), "\\" + "u970d\\" + "u83b1\\" + "u6c83")


def _scan_public_tree(root: Path) -> list[str]:
    findings: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or any(part in PUBLIC_SCAN_EXCLUDED for part in path.relative_to(root).parts):
            continue
        if path.name == ".env" or path.name.endswith(".local.json"):
            continue
        if path.suffix.lower() not in PUBLIC_TEXT_SUFFIXES and path.name not in {".gitignore", ".gitattributes"}:
            continue
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            continue
        relative = path.relative_to(root).as_posix()
        if re.search(r"[A-Za-z]:\\(?:Users|CodexWorkspace)\\", text, flags=re.IGNORECASE):
            findings.append(f"{relative}: machine-specific absolute path")
        if LIVE_FEISHU_WEBHOOK.search(text):
            findings.append(f"{relative}: possible live Feishu webhook")
        if any(term.lower() in text.lower() for term in PRIVATE_PUBLIC_TERMS):
            findings.append(f"{relative}: private company term in public content")
        if "?" * 3 in text or "\ufffd" in text:
            findings.append(f"{relative}: possible text-encoding corruption")
    return findings


def _resolve(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def _check(name: str, status: str, detail: str) -> dict[str, str]:
    return {"check": name, "status": status, "detail": detail}


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _find_placeholders(value: Any, location: str = "root") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            hits.extend(_find_placeholders(item, f"{location}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            hits.extend(_find_placeholders(item, f"{location}[{index}]"))
    elif isinstance(value, str) and ("?" * 3 in value or "\ufffd" in value):
        hits.append(location)
    return hits


def run_release_check(
    project_root: str | Path = ".",
    db_path: str | Path = "data/bids.db",
    profile_path: str | Path = "config/profile.json",
    sources_path: str | Path = "config/sources.json",
) -> tuple[bool, list[dict[str, str]]]:
    """Run deterministic, offline checks required before sharing a release."""
    root = Path(project_root).resolve()
    checks: list[dict[str, str]] = []
    ok = True

    missing = [relative for relative in REQUIRED_PATHS if not (root / relative).is_file()]
    if missing:
        ok = False
        checks.append(_check("repository files", "error", "missing: " + ", ".join(missing)))
    else:
        checks.append(_check("repository files", "ok", f"{len(REQUIRED_PATHS)} required files found"))

    profile: dict[str, Any] = {}
    profile_file = _resolve(root, profile_path)
    try:
        loaded = _load_json(profile_file)
        if not isinstance(loaded, dict):
            raise ValueError("top level must be a JSON object")
        profile = loaded
        checks.append(_check("profile JSON", "ok", str(profile_file)))
    except Exception as exc:
        ok = False
        checks.append(_check("profile JSON", "error", f"{profile_file}: {exc}"))

    if profile:
        profile_schema_errors = validate_config(profile_file, "profile")
        if profile_schema_errors:
            ok = False
        checks.append(_check(
            "profile schema", "error" if profile_schema_errors else "ok",
            "; ".join(profile_schema_errors[:5]) if profile_schema_errors else "valid against bundled profile schema",
        ))
        business_lines = profile.get("business_lines", [])
        valid_lines = [
            row for row in business_lines
            if isinstance(row, dict)
            and row.get("id")
            and row.get("name")
            and (row.get("strong_terms") or row.get("related_terms"))
        ] if isinstance(business_lines, list) else []
        lines_ok = bool(business_lines) and len(valid_lines) == len(business_lines)
        if not lines_ok:
            ok = False
        checks.append(_check(
            "business lines", "ok" if lines_ok else "error",
            f"{len(valid_lines)} valid of {len(business_lines) if isinstance(business_lines, list) else 0}; at least one is required",
        ))

    sources: dict[str, Any] = {}
    sources_file = _resolve(root, sources_path)
    try:
        loaded = _load_json(sources_file)
        if not isinstance(loaded, dict):
            raise ValueError("top level must be a JSON object")
        sources = loaded
        checks.append(_check("sources JSON", "ok", str(sources_file)))
    except Exception as exc:
        ok = False
        checks.append(_check("sources JSON", "error", f"{sources_file}: {exc}"))

    if sources:
        source_schema_errors = validate_config(sources_file, "sources")
        if source_schema_errors:
            ok = False
        checks.append(_check(
            "sources schema", "error" if source_schema_errors else "ok",
            "; ".join(source_schema_errors[:5]) if source_schema_errors else "valid against bundled sources schema",
        ))
        source_rows = sources.get("sources", [])
        enabled = [row for row in source_rows if isinstance(row, dict) and row.get("enabled", True)] if isinstance(source_rows, list) else []
        enabled_ok = bool(enabled)
        if not enabled_ok:
            ok = False
        checks.append(_check("enabled sources", "ok" if enabled_ok else "error", f"{len(enabled)} enabled"))

    placeholder_hits = _find_placeholders({"profile": profile, "sources": sources})
    if placeholder_hits:
        ok = False
        checks.append(_check("config placeholders", "error", "found repeated question marks or Unicode replacement character at: " + ", ".join(placeholder_hits[:10])))
    else:
        checks.append(_check("config placeholders", "ok", "no repeated question marks or Unicode replacement characters"))

    db_file = _resolve(root, db_path)
    try:
        db_file.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(db_file) as connection:
            connection.execute("SELECT 1")
        checks.append(_check("SQLite", "ok", str(db_file)))
    except Exception as exc:
        ok = False
        checks.append(_check("SQLite", "error", f"{db_file}: {exc}"))

    gitignore = root / ".gitignore"
    try:
        ignored = {line.strip() for line in gitignore.read_text(encoding="utf-8-sig").splitlines() if line.strip() and not line.lstrip().startswith("#")}
        secrets_ok = ".env" in ignored and "data/*.db" in ignored and "data/**/*.db" in ignored and "reports/**" in ignored and "config/*.local.json" in ignored
        if not secrets_ok:
            ok = False
        detail = ".env, databases, and generated reports are ignored" if secrets_ok else ".gitignore must ignore .env, local profiles, data/*.db, data/**/*.db, and reports/**"
        checks.append(_check("sensitive-file ignores", "ok" if secrets_ok else "error", detail))
    except Exception as exc:
        ok = False
        checks.append(_check("sensitive-file ignores", "error", str(exc)))


    public_findings = _scan_public_tree(root)
    if public_findings:
        ok = False
        checks.append(_check("public content scan", "error", "; ".join(public_findings[:10])))
    else:
        checks.append(_check("public content scan", "ok", "no machine-specific paths, live Feishu webhooks, or private company terms"))

    env_example = root / ".env.example"
    try:
        values = {}
        for line in env_example.read_text(encoding="utf-8-sig").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
        example_ok = not any(values.values())
        if not example_ok:
            ok = False
        checks.append(_check("environment example", "ok" if example_ok else "error", "all example secret values are empty" if example_ok else ".env.example contains a non-empty value"))
    except Exception as exc:
        ok = False
        checks.append(_check("environment example", "error", str(exc)))

    version = tuple(int(part) for part in platform.python_version_tuple())
    python_ok = version >= (3, 11, 0)
    if not python_ok:
        ok = False
    checks.append(_check("Python", "ok" if python_ok else "error", platform.python_version()))
    checks.append(_check("network access", "ok", "release check made no network requests"))
    return ok, checks
