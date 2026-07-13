from __future__ import annotations

import json
from pathlib import Path

import pytest

from bid_intel.cli import main
from bid_intel.models import Notice
from bid_intel.routing import build_routing_report, render_routing_markdown
from bid_intel.storage import Store


def profile(profile_id: str, title: str, strong_terms: list[str], related_terms: list[str] | None = None) -> dict:
    return {
        "meta": {"id": profile_id, "title": title},
        "business_lines": [{
            "id": f"{profile_id}-line",
            "name": title,
            "base_score": 20,
            "strong_terms": strong_terms,
            "related_terms": related_terms or [],
        }],
        "buyer_terms": [],
        "procurement_terms": [],
        "negative_terms": [],
        "stage_weights": {},
        "sales_profile": {"focus_regions": [], "priority_accounts": [], "minimum_followup_amount_cny": 0},
    }


def test_routes_notices_to_best_profile_with_deterministic_alternatives():
    notices = [
        (1, Notice(
            title="Cloud migration platform",
            url="https://example.invalid/cloud",
            source="fixture",
            published_at="2026-07-13",
            content="cloud migration services and security controls",
        )),
        (2, Notice(
            title="School laboratory equipment",
            url="https://example.invalid/lab",
            source="fixture",
            published_at="2026-07-12",
            content="classroom scientific laboratory instruments",
        )),
        (3, Notice(
            title="Office stationery",
            url="https://example.invalid/office",
            source="fixture",
            published_at="2026-07-11",
        )),
    ]
    profiles = [
        profile("security", "Security", ["security"]),
        profile("cloud", "Cloud", ["cloud"], ["migration"]),
        profile("education", "Education", ["laboratory"], ["classroom", "scientific"]),
    ]

    report = build_routing_report(notices, profiles, min_score=30, top_profiles=2)

    assert report["notice_count"] == 3
    assert report["matched_notice_count"] == 2
    assert report["unmatched_notice_count"] == 1
    assert [row["assigned_profile"]["profile_id"] for row in report["routes"]] == ["education", "cloud"]
    cloud = next(row for row in report["routes"] if row["notice_id"] == 1)
    assert cloud["assigned_profile"]["score"] > cloud["alternatives"][0]["score"]
    assert cloud["alternatives"][0]["profile_id"] == "security"
    assert "content" not in cloud
    assert "raw" not in cloud


def test_ties_use_profile_id_and_limit_does_not_change_match_counts():
    notice = Notice(
        title="Shared platform",
        url="https://example.invalid/shared",
        source="fixture",
        published_at="2026-07-13",
        content="shared",
    )
    profiles = [profile("z-team", "Z team", ["shared"]), profile("a-team", "A team", ["shared"])]

    report = build_routing_report([(1, notice), (2, notice)], profiles, min_score=30, limit=1, top_profiles=2)

    assert report["matched_notice_count"] == 2
    assert report["returned_notice_count"] == 1
    assert report["routes"][0]["assigned_profile"]["profile_id"] == "a-team"
    assert report["routes"][0]["alternatives"][0]["profile_id"] == "z-team"


def test_cli_routes_with_all_bundled_profiles_without_writing_scores(tmp_path, capsys):
    database = tmp_path / "bids.db"
    store = Store(database)
    notice_id, _ = store.upsert_notice(Notice(
        title="University smart classroom and learning platform",
        url="https://example.invalid/education",
        source="fixture",
        published_at="2026-07-13",
        buyer="Example University",
        content="digital learning platform, lecture capture, and classroom displays",
    ))
    store.add_feedback(notice_id, "related", "private note must stay private")

    assert main(["--db", str(database), "route", "--min-score", "20", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["profile_count"] >= 9
    assert payload["routes"][0]["assigned_profile"]["profile_id"] == "education"
    assert "private note" not in json.dumps(payload)
    assert Store(database).stats()["scores"] == 0

    output = tmp_path / "routing.json"
    assert main([
        "--db", str(database), "route", "--profile-id", "education",
        "--min-score", "20", "--json", "--output", str(output),
    ]) == 0
    assert "Routing report generated" in capsys.readouterr().out
    assert json.loads(output.read_text(encoding="utf-8"))["profile_count"] == 1


def test_cli_custom_profiles_and_duplicate_ids(tmp_path, capsys):
    database = tmp_path / "bids.db"
    Store(database)
    custom = tmp_path / "custom.json"
    root = Path(__file__).resolve().parents[1]
    custom.write_text((root / "src/bid_intel/profiles/education.json").read_text(encoding="utf-8"), encoding="utf-8")

    assert main([
        "--db", str(database), "route",
        "--profile-id", "education", "--profile-path", str(custom),
    ]) == 2
    assert "duplicate routing profile id: education" in capsys.readouterr().err


@pytest.mark.parametrize("option,value", [
    ("--min-score", "101"),
    ("--limit", "0"),
    ("--top-profiles", "0"),
])
def test_cli_rejects_invalid_route_limits(tmp_path, option, value):
    with pytest.raises(SystemExit) as error:
        main(["--db", str(tmp_path / "bids.db"), "route", option, value])
    assert error.value.code == 2


def test_cli_rejects_invalid_route_as_of(tmp_path, capsys):
    assert main([
        "--db", str(tmp_path / "bids.db"), "route", "--as-of", "not-a-date",
    ]) == 2
    assert "--as-of must be an ISO date" in capsys.readouterr().err


def test_empty_database_report_is_clear():
    report = build_routing_report([], [profile("team", "Team", ["shared"])])

    assert report["notice_count"] == 0
    assert report["matched_notice_count"] == 0
    assert report["routes"] == []
    assert "No notices met" in render_routing_markdown(report)


def test_markdown_escapes_headings_and_unsafe_links():
    notice = Notice(
        title="# Heading|break\nnext",
        url="https://example.invalid/> injected",
        source="fixture",
        published_at="2026-07-13",
        content="shared",
    )
    report = build_routing_report([(1, notice)], [profile("team", "Team|One", ["shared"])], min_score=1)

    markdown = render_routing_markdown(report)

    assert "### 1. \\# Heading|break next" in markdown
    assert "Team\\|One" in markdown
    assert "Official notice" not in markdown
