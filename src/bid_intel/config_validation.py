from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Any


SCHEMA_FILES = {"profile": "profile.schema.json", "sources": "sources.schema.json"}


def load_schema(kind: str) -> dict[str, Any]:
    try:
        name = SCHEMA_FILES[kind]
    except KeyError as exc:
        raise ValueError(f"unknown schema kind: {kind}") from exc
    source_tree = Path(__file__).resolve().parents[2] / "schemas" / name
    if source_tree.is_file():
        return json.loads(source_tree.read_text(encoding="utf-8"))
    resource = files("bid_intel").joinpath("schemas", name)
    return json.loads(resource.read_text(encoding="utf-8"))


def validate_config_instance(instance: Any, kind: str) -> list[str]:
    errors = validate_instance(instance, load_schema(kind))
    if not errors:
        errors.extend(_semantic_errors(instance, kind))
    return errors


def validate_config(path: str | Path, kind: str) -> list[str]:
    target = Path(path)
    try:
        instance = json.loads(target.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return [f"$: file not found: {target}"]
    except json.JSONDecodeError as exc:
        return [f"$: invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"]
    return validate_config_instance(instance, kind)


def validate_instance(instance: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    errors: list[str] = []
    expected = schema.get("type")
    if expected and not _matches_type(instance, expected):
        return [f"{path}: expected {expected}, got {_type_name(instance)}"]

    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: value must be one of {schema['enum']}")
    if isinstance(instance, str):
        minimum = schema.get("minLength")
        if minimum is not None and len(instance) < int(minimum):
            errors.append(f"{path}: string must contain at least {minimum} character(s)")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        minimum = schema.get("minimum")
        if minimum is not None and instance < minimum:
            errors.append(f"{path}: value must be at least {minimum}")
    if isinstance(instance, list):
        minimum = schema.get("minItems")
        if minimum is not None and len(instance) < int(minimum):
            errors.append(f"{path}: array must contain at least {minimum} item(s)")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(instance):
                errors.extend(validate_instance(item, item_schema, f"{path}[{index}]"))
    if isinstance(instance, dict):
        properties = schema.get("properties", {})
        for name in schema.get("required", []):
            if name not in instance:
                errors.append(f"{path}: missing required property {name!r}")
        for name, value in instance.items():
            if name in properties:
                errors.extend(validate_instance(value, properties[name], f"{path}.{name}"))
                continue
            additional = schema.get("additionalProperties", True)
            if additional is False:
                errors.append(f"{path}: unexpected property {name!r}")
            elif isinstance(additional, dict):
                errors.extend(validate_instance(value, additional, f"{path}.{name}"))
    return errors


def _semantic_errors(instance: Any, kind: str) -> list[str]:
    if not isinstance(instance, dict):
        return []
    key = "business_lines" if kind == "profile" else "sources"
    rows = instance.get(key, [])
    if not isinstance(rows, list):
        return []
    ids = [row.get("id") for row in rows if isinstance(row, dict) and row.get("id")]
    duplicates = sorted({value for value in ids if ids.count(value) > 1})
    return [f"$.{key}: duplicate id {value!r}" for value in duplicates]


def _matches_type(value: Any, expected: str | list[str]) -> bool:
    if isinstance(expected, list):
        return any(_matches_type(value, item) for item in expected)
    checks = {
        "object": lambda item: isinstance(item, dict),
        "array": lambda item: isinstance(item, list),
        "string": lambda item: isinstance(item, str),
        "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "boolean": lambda item: isinstance(item, bool),
        "null": lambda item: item is None,
    }
    return checks.get(expected, lambda _item: True)(value)


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
