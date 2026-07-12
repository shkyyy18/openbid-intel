from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

from .models import Notice


FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "title": ("title", "name", "project_name", "notice_title", "subject", "\u9879\u76ee\u540d\u79f0", "\u516c\u544a\u6807\u9898"),
    "url": ("url", "link", "notice_url", "source_url", "\u7f51\u5740", "\u94fe\u63a5"),
    "source": ("source", "portal", "source_name", "platform", "\u6765\u6e90", "\u5e73\u53f0"),
    "published_at": ("published_at", "publish_date", "published", "date", "release_date", "\u53d1\u5e03\u65f6\u95f4", "\u53d1\u5e03\u65e5\u671f"),
    "deadline_at": ("deadline_at", "deadline", "closing_date", "bid_deadline", "\u622a\u6b62\u65f6\u95f4", "\u6295\u6807\u622a\u6b62\u65f6\u95f4"),
    "stage": ("stage", "notice_type", "type", "status", "\u516c\u544a\u7c7b\u578b", "\u9636\u6bb5"),
    "buyer": ("buyer", "purchaser", "buyer_name", "agency", "organization", "\u91c7\u8d2d\u4eba", "\u91c7\u8d2d\u5355\u4f4d"),
    "region": ("region", "location", "province", "area", "\u5730\u533a", "\u7701\u4efd"),
    "budget_cny": ("budget_cny", "budget", "amount", "estimated_value", "project_budget", "\u9884\u7b97", "\u9884\u7b97\u91d1\u989d"),
    "content": ("content", "description", "summary", "body", "details", "\u6b63\u6587", "\u6458\u8981"),
    "project_id": ("project_id", "project_code", "notice_id", "reference", "\u9879\u76ee\u7f16\u53f7", "\u516c\u544a\u7f16\u53f7"),
    "award_supplier": ("award_supplier", "winner", "supplier", "vendor", "\u4e2d\u6807\u4f9b\u5e94\u5546", "\u4e2d\u6807\u4eba"),
    "award_amount_cny": ("award_amount_cny", "award_amount", "contract_value", "\u4e2d\u6807\u91d1\u989d", "\u6210\u4ea4\u91d1\u989d"),
}


def load_notices(path: str | Path, mapping_path: str | Path | None = None) -> list[Notice]:
    source = Path(path)
    mapping = _load_mapping(mapping_path)
    rows = _load_rows(source)
    notices = []
    for item in rows:
        record = canonicalize_record(item, mapping)
        record.setdefault("source", source_name_or_default(source))
        notices.append(Notice.from_dict(record))
    return notices


def canonicalize_record(item: dict[str, Any], mapping: dict[str, str] | None = None) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError("each notice must be a JSON object or CSV row")
    mapping = mapping or {}
    lower_keys = {str(key).strip().lower(): key for key in item}
    result: dict[str, Any] = {}
    for canonical, aliases in FIELD_ALIASES.items():
        source_name = mapping.get(canonical)
        candidates = (source_name,) if source_name else aliases
        for candidate in candidates:
            if not candidate:
                continue
            actual = lower_keys.get(str(candidate).strip().lower())
            if actual is not None and item.get(actual) not in (None, ""):
                result[canonical] = item[actual]
                break
    for amount_field in ("budget_cny", "award_amount_cny"):
        if amount_field in result:
            result[amount_field] = _parse_amount(result[amount_field])
    result["raw"] = dict(item)
    return result


def _load_rows(source: Path) -> list[dict[str, Any]]:
    suffix = source.suffix.lower()
    if suffix == ".json":
        with source.open("r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
        if isinstance(payload, dict):
            payload = payload.get("notices", payload.get("items", payload.get("results", [payload])))
        if not isinstance(payload, list):
            raise ValueError("JSON must be an array or contain a notices/items/results array")
        return payload
    if suffix == ".jsonl":
        with source.open("r", encoding="utf-8-sig") as handle:
            return [json.loads(line) for line in handle if line.strip()]
    if suffix == ".csv":
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    raise ValueError("supported formats: .json, .jsonl, .csv")


def _load_mapping(path: str | Path | None) -> dict[str, str]:
    if not path:
        return {}
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("field mapping must be a JSON object of canonical_name -> source_name")
    unknown = sorted(set(data) - set(FIELD_ALIASES))
    if unknown:
        raise ValueError("unknown canonical mapping fields: " + ", ".join(unknown))
    return {str(key): str(value) for key, value in data.items()}


def _parse_amount(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().lower().replace(",", "")
    multiplier = 1.0
    if "million" in text:
        multiplier = 1_000_000.0
    elif "billion" in text:
        multiplier = 1_000_000_000.0
    elif "\u4e07" in text:
        multiplier = 10_000.0
    elif "\u4ebf" in text:
        multiplier = 100_000_000.0
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(match.group(0)) * multiplier if match else None


def source_name_or_default(path: Path) -> str:
    return path.stem or "import"
