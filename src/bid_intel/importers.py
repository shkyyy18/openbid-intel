from __future__ import annotations

import csv
import json
from pathlib import Path

from .models import Notice


def load_notices(path: str | Path) -> list[Notice]:
    source = Path(path)
    suffix = source.suffix.lower()
    if suffix == ".json":
        with source.open("r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
        if isinstance(payload, dict):
            payload = payload.get("notices", [payload])
        if not isinstance(payload, list):
            raise ValueError("JSON 顶层必须是公告数组，或包含 notices 数组")
        return [Notice.from_dict(item) for item in payload]
    if suffix == ".jsonl":
        with source.open("r", encoding="utf-8-sig") as handle:
            return [Notice.from_dict(json.loads(line)) for line in handle if line.strip()]
    if suffix == ".csv":
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            return [Notice.from_dict(dict(row)) for row in csv.DictReader(handle)]
    raise ValueError("仅支持 .json、.jsonl、.csv")
