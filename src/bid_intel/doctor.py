from __future__ import annotations

import json
import os
import platform
import sqlite3
import urllib.request
from pathlib import Path

from .collectors import load_sources
from .notifier import load_dotenv


def run_doctor(db_path: str | Path, profile_path: str | Path, sources_path: str | Path) -> tuple[bool, list[dict[str, str]]]:
    load_dotenv()
    checks: list[dict[str, str]] = []
    ok = True

    for name, path in (("企业画像", Path(profile_path)), ("来源配置", Path(sources_path))):
        try:
            with path.open("r", encoding="utf-8-sig") as handle:
                json.load(handle)
            checks.append({"check": name, "status": "ok", "detail": str(path)})
        except Exception as exc:
            ok = False
            checks.append({"check": name, "status": "error", "detail": str(exc)})

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
