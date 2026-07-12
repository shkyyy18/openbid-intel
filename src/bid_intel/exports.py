from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


CRM_FIELDS = (
    "notice_id",
    "title",
    "buyer",
    "region",
    "budget_cny",
    "stage",
    "score",
    "business_lines",
    "published_at",
    "deadline_at",
    "url",
    "latest_verdict",
)


def write_crm_csv(path: str | Path, rows: list[dict[str, Any]]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CRM_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            result = row.get("result") if isinstance(row.get("result"), dict) else {}
            writer.writerow({
                "notice_id": row.get("id", ""),
                "title": row.get("title", ""),
                "buyer": row.get("buyer", ""),
                "region": row.get("region", ""),
                "budget_cny": _cell(row.get("budget_cny")),
                "stage": row.get("stage", ""),
                "score": _cell(row.get("score")),
                "business_lines": "; ".join(str(item) for item in result.get("business_lines", [])),
                "published_at": row.get("published_at", ""),
                "deadline_at": row.get("deadline_at", ""),
                "url": row.get("url", ""),
                "latest_verdict": row.get("latest_verdict", ""),
            })
    return target


def _cell(value: Any) -> Any:
    return "" if value is None else value
