from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Any


def _profile_files():
    root = files("bid_intel").joinpath("profiles")
    return sorted((item for item in root.iterdir() if item.name.endswith(".json")), key=lambda item: item.name)


def list_profiles() -> list[dict[str, str]]:
    rows = []
    for item in _profile_files():
        data = json.loads(item.read_text(encoding="utf-8"))
        meta = data.get("meta", {})
        rows.append({
            "id": str(meta.get("id") or item.name.removesuffix(".json")),
            "title": str(meta.get("title") or item.name),
            "description": str(meta.get("description") or ""),
        })
    return rows


def load_builtin_profile(profile_id: str) -> dict[str, Any]:
    wanted = profile_id.strip().lower()
    for item in _profile_files():
        if item.name.removesuffix(".json") == wanted:
            return json.loads(item.read_text(encoding="utf-8"))
    available = ", ".join(row["id"] for row in list_profiles())
    raise ValueError(f"unknown profile {profile_id!r}; choose one of: {available}")


def write_profile(profile_id: str, output: str | Path, force: bool = False) -> Path:
    target = Path(output)
    if target.exists() and not force:
        raise FileExistsError(f"{target} already exists; pass --force to replace it")
    data = load_builtin_profile(profile_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target
