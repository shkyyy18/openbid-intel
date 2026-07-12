from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TextIO

from .config_validation import validate_config
from .profiles import list_profiles, write_profile

SOURCES_SCHEMA_URL = "https://shkyyy18.github.io/openbid-intel/schemas/sources.schema.json"


def choose_profile(input_stream: TextIO = sys.stdin, output_stream: TextIO = sys.stdout) -> str:
    profiles = list_profiles()
    default_id = "it-digital"
    print("Choose an industry profile:", file=output_stream)
    for index, row in enumerate(profiles, start=1):
        marker = " (default)" if row["id"] == default_id else ""
        print(f"  {index}. {row['id']}: {row['title']}{marker}", file=output_stream)
    print("Profile number or ID [it-digital]: ", end="", file=output_stream, flush=True)
    answer = input_stream.readline().strip()
    if not answer:
        return default_id
    if answer.isdigit() and 1 <= int(answer) <= len(profiles):
        return profiles[int(answer) - 1]["id"]
    ids = {row["id"] for row in profiles}
    if answer in ids:
        return answer
    raise ValueError(f"unknown profile {answer!r}; run 'openbid profiles' to list choices")


def source_template(kind: str) -> dict:
    base = {
        "$schema": SOURCES_SCHEMA_URL,
        "request_interval_seconds": 1.0,
        "history_days": 30,
        "sources": [],
    }
    if kind == "empty":
        return base
    if kind == "rss":
        base["sources"] = [{
            "id": "replace-with-feed-id",
            "name": "Replace with a permitted public procurement feed",
            "type": "rss_atom",
            "url": "https://example.invalid/procurement/feed.xml",
            "stage": "notice",
            "enabled": False,
            "note": "Replace the URL, verify access terms, then set enabled to true.",
        }]
        return base
    raise ValueError(f"unknown source template: {kind}")


def write_sources(kind: str, output: str | Path, force: bool = False) -> Path:
    target = Path(output)
    if target.exists() and not force:
        raise FileExistsError(f"{target} already exists; pass --force to replace it")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(source_template(kind), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def initialize(
    preset: str,
    profile_output: str | Path,
    sources_output: str | Path,
    source_kind: str = "empty",
    force: bool = False,
) -> tuple[Path, Path]:
    profile_target = Path(profile_output)
    sources_target = Path(sources_output)
    for target in (profile_target, sources_target):
        if target.exists() and not force:
            raise FileExistsError(f"{target} already exists; pass --force to replace it")
    write_profile(preset, profile_target, force=force)
    write_sources(source_kind, sources_target, force=force)
    errors = validate_config(profile_target, "profile") + validate_config(sources_target, "sources")
    if errors:
        raise ValueError("generated invalid configuration: " + "; ".join(errors))
    return profile_target, sources_target
