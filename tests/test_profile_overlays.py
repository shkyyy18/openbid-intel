from __future__ import annotations

import json
from pathlib import Path

import pytest

from bid_intel.cli import main
from bid_intel.profiles import (
    ProfileConfigError,
    load_builtin_profile,
    load_composed_profile,
    merge_profile,
)


def write_json(path: Path, data) -> Path:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def test_overlay_merges_keyed_objects_and_deduplicates_scalar_lists():
    base = load_builtin_profile("education")
    line_id = base["business_lines"][0]["id"]
    original_terms = list(base["business_lines"][0]["strong_terms"])
    overlay = {
        "buyer_terms": [base["buyer_terms"][0], "synthetic research buyer"],
        "business_lines": [{"id": line_id, "strong_terms": [original_terms[0], "private product phrase"]}],
        "sales_profile": {
            "priority_accounts": [
                {"name": "Synthetic Account", "aliases": ["Synthetic Alias"], "weight": 30}
            ]
        },
    }

    merged = merge_profile(base, overlay)

    assert merged["buyer_terms"].count(base["buyer_terms"][0]) == 1
    assert merged["buyer_terms"][-1] == "synthetic research buyer"
    line = next(item for item in merged["business_lines"] if item["id"] == line_id)
    assert line["name"] == base["business_lines"][0]["name"]
    assert line["strong_terms"][-1] == "private product phrase"
    assert line["strong_terms"].count(original_terms[0]) == 1
    assert merged["sales_profile"]["priority_accounts"][0]["name"] == "Synthetic Account"
    assert "private product phrase" not in base["business_lines"][0]["strong_terms"]


def test_multiple_overlays_apply_left_to_right_and_empty_list_clears(tmp_path):
    base = write_json(tmp_path / "base.json", load_builtin_profile("education"))
    first = write_json(tmp_path / "first.local.json", {
        "buyer_terms": ["first buyer"],
        "sales_profile": {
            "priority_accounts": [
                {"name": "Synthetic Account", "aliases": ["Alias One"], "weight": 20}
            ]
        },
    })
    second = write_json(tmp_path / "second.local.json", {
        "buyer_terms": [],
        "sales_profile": {
            "priority_accounts": [
                {"name": "Synthetic Account", "aliases": ["Alias Two"], "weight": 35}
            ]
        },
    })

    profile = load_composed_profile(base, [first, second])

    assert profile["buyer_terms"] == []
    account = profile["sales_profile"]["priority_accounts"][0]
    assert account["aliases"] == ["Alias One", "Alias Two"]
    assert account["weight"] == 35


def test_invalid_overlay_reports_composed_schema_errors(tmp_path):
    base = write_json(tmp_path / "base.json", load_builtin_profile("education"))
    overlay = write_json(tmp_path / "broken.local.json", {
        "business_lines": [{"id": "new-incomplete-line"}]
    })

    with pytest.raises(ProfileConfigError) as caught:
        load_composed_profile(base, [overlay])

    assert "broken.local.json" in caught.value.source
    assert any("missing required property 'name'" in error for error in caught.value.errors)


def test_non_object_overlay_is_rejected_with_source_path(tmp_path):
    base = write_json(tmp_path / "base.json", load_builtin_profile("education"))
    overlay = write_json(tmp_path / "broken.local.json", ["not", "an", "object"])

    with pytest.raises(ProfileConfigError) as caught:
        load_composed_profile(base, [overlay])

    assert caught.value.source.endswith("broken.local.json")
    assert caught.value.errors == ["$: expected object, got array"]


def test_cli_explain_uses_private_overlay_without_writing_database_or_exposing_it(tmp_path, capsys):
    root = Path(__file__).resolve().parents[1]
    database = tmp_path / "must-not-exist.db"
    overlay = write_json(tmp_path / "profile.local.json", {
        "business_lines": [{
            "id": "digital_learning",
            "strong_terms": ["synthetic private product phrase"],
        }]
    })
    base = root / "src/bid_intel/profiles/education.json"

    rc = main([
        "--db", str(database),
        "--profile", str(base),
        "--profile-overlay", str(overlay),
        "explain", "--title", "Synthetic private product phrase procurement", "--json",
    ])

    assert rc == 0
    assert not database.exists()
    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == str(base)
    assert str(overlay) not in json.dumps(payload)
    assert "Education technology and digital learning" in payload["business_lines"]


def test_cli_validate_config_composes_profile_overlays(tmp_path, capsys):
    root = Path(__file__).resolve().parents[1]
    overlay = write_json(tmp_path / "profile.local.json", {"buyer_terms": ["synthetic buyer"]})

    rc = main([
        "--profile", str(root / "src/bid_intel/profiles/education.json"),
        "--profile-overlay", str(overlay),
        "validate-config", "--only", "profile",
    ])

    assert rc == 0
    assert "+ 1 overlay(s)" in capsys.readouterr().out

