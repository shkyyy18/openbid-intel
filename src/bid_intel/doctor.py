from __future__ import annotations

import json
import os
import platform
import sqlite3
import urllib.request
from pathlib import Path

from .collectors import load_sources
from .notifier import load_dotenv
from .profiles import ProfileConfigError, load_composed_profile


def run_doctor(
    db_path: str | Path,
    profile_path: str | Path,
    sources_path: str | Path,
    profile_overlays: list[str | Path] | None = None,
) -> tuple[bool, list[dict[str, str]]]:
    load_dotenv()
    checks: list[dict[str, str]] = []
    ok = True

    try:
        load_composed_profile(profile_path, profile_overlays)
        overlay_detail = f" + {len(profile_overlays)} overlay(s)" if profile_overlays else ""
        checks.append({"check": "Profile", "status": "ok", "detail": f"{profile_path}{overlay_detail}"})
    except ProfileConfigError as exc:
        ok = False
        checks.append({"check": "Profile", "status": "error", "detail": str(exc)})

    source_path = Path(sources_path)
    try:
        with source_path.open("r", encoding="utf-8-sig") as handle:
            json.load(handle)
        checks.append({"check": "Sources", "status": "ok", "detail": str(source_path)})
    except Exception as exc:
        ok = False
        checks.append({"check": "Sources", "status": "error", "detail": str(exc)})

    try:
        db = Path(db_path)
        db.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(db) as connection:
            connection.execute("SELECT 1")
        checks.append({"check": "SQLite", "status": "ok", "detail": str(db)})
    except Exception as exc:
        ok = False
        checks.append({"check": "SQLite", "status": "error", "detail": str(exc)})

    try:
        sources = load_sources(sources_path).get("sources", [])
        enabled = [item for item in sources if item.get("enabled", True)]
        checks.append({"check": "数据来源", "status": "ok" if enabled else "warning", "detail": f"启用 {len(enabled)} 个"})
    except Exception:
        pass

    webhook = os.getenv("FEISHU_WEBHOOK_URL", "")
    checks.append({"check": "飞书 Webhook", "status": "ok" if webhook else "warning", "detail": "已配置" if webhook else "未配置，仅生成本地日报"})
    checks.append({"check": "运行环境", "status": "ok", "detail": f"Python {platform.python_version()} / {platform.system()}"})
    return ok, checks
