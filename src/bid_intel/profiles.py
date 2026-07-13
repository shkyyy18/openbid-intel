from __future__ import annotations

import copy
import json
from importlib.resources import files
from pathlib import Path
from typing import Any

from .config_validation import validate_config_instance


class ProfileConfigError(ValueError):
    """Raised when a base profile or overlay cannot produce a valid profile."""

    def __init__(self, source: str | Path, errors: list[str]):
        self.source = str(source)
        self.errors = errors
        super().__init__(f"invalid profile configuration {self.source}: {'; '.join(errors)}")


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


def load_profile_file(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    try:
        data = json.loads(target.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise ProfileConfigError(target, ["$: file not found"]) from None
    except json.JSONDecodeError as exc:
        raise ProfileConfigError(
            target, [f"$: invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"]
        ) from None
    if not isinstance(data, dict):
        raise ProfileConfigError(target, [f"$: expected object, got {_type_name(data)}"])
    return data


def merge_profile(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic deep merge without mutating either input."""
    if not isinstance(base, dict) or not isinstance(overlay, dict):
        raise TypeError("profile base and overlay must both be objects")
    return _merge_value(base, overlay, ())


def load_composed_profile(
    profile_path: str | Path,
    overlay_paths: list[str | Path] | tuple[str | Path, ...] | None = None,
) -> dict[str, Any]:
    profile = load_profile_file(profile_path)
    errors = validate_config_instance(profile, "profile")
    if errors:
        raise ProfileConfigError(profile_path, errors)

    applied: list[str] = []
    for overlay_path in overlay_paths or ():
        overlay = load_profile_file(overlay_path)
        profile = merge_profile(profile, overlay)
        applied.append(str(overlay_path))

    errors = validate_config_instance(profile, "profile")
    if errors:
        label = " + ".join([str(profile_path), *applied])
        raise ProfileConfigError(label, errors)
    return profile


def write_profile(profile_id: str, output: str | Path, force: bool = False) -> Path:
    target = Path(output)
    if target.exists() and not force:
        raise FileExistsError(f"{target} already exists; pass --force to replace it")
    data = load_builtin_profile(profile_id)
    data = {"$schema": "https://shkyyy18.github.io/openbid-intel/schemas/profile.schema.json", **data}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def _merge_value(base: Any, overlay: Any, path: tuple[str, ...]) -> Any:
    if isinstance(base, dict) and isinstance(overlay, dict):
        result = copy.deepcopy(base)
        for key, value in overlay.items():
            result[key] = _merge_value(result[key], value, (*path, key)) if key in result else copy.deepcopy(value)
        return result
    if isinstance(base, list) and isinstance(overlay, list):
        return _merge_list(base, overlay, path)
    return copy.deepcopy(overlay)


def _merge_list(base: list[Any], overlay: list[Any], path: tuple[str, ...]) -> list[Any]:
    if not overlay:
        return []

    key = _list_merge_key(path, base, overlay)
    if key:
        result = copy.deepcopy(base)
        positions = {
            item.get(key): index
            for index, item in enumerate(result)
            if isinstance(item, dict) and item.get(key) not in (None, "")
        }
        for item in overlay:
            if not isinstance(item, dict) or item.get(key) in (None, ""):
                result.append(copy.deepcopy(item))
                continue
            identity = item[key]
            if identity in positions:
                index = positions[identity]
                result[index] = _merge_value(result[index], item, (*path, str(identity)))
            else:
                positions[identity] = len(result)
                result.append(copy.deepcopy(item))
        return result

    if all(not isinstance(item, (dict, list)) for item in [*base, *overlay]):
        result: list[Any] = []
        for item in [*base, *overlay]:
            if item not in result:
                result.append(copy.deepcopy(item))
        return result

    return copy.deepcopy(overlay)


def _list_merge_key(path: tuple[str, ...], base: list[Any], overlay: list[Any]) -> str | None:
    if path and path[-1] == "business_lines":
        return "id"
    if path and path[-1] == "priority_accounts":
        return "name"
    dictionaries = [item for item in [*base, *overlay] if isinstance(item, dict)]
    if dictionaries and len(dictionaries) == len(base) + len(overlay):
        for candidate in ("id", "name"):
            if all(item.get(candidate) not in (None, "") for item in dictionaries):
                return candidate
    return None


def _type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    return type(value).__name__
