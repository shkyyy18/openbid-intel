from __future__ import annotations

import json
from pathlib import Path

import pytest

from bid_intel.calibration import build_calibration_report, render_calibration_markdown
from bid_intel.cli import main
from bid_intel.models import Notice, ScoreResult
from bid_intel.storage import Store


def score_result(score: int) -> ScoreResult:
    return ScoreResult(
        score=score,
        level="test",
        business_lines=[],
        strong_hits=[],
        related_hits=[],
        buyer_hits=[],
        negative_hits=[],
        reasons=[],
        risks=[],
        recommended_actions=[],
    )


def seed_calibration_store(path: Path) -> Store:
    store = Store(path)
    examples = [
        ("High false positive", 90, ["相关", "不相关"]),
        ("High true positive", 80, ["已跟进"]),
        ("Ambiguous workflow outcome", 60, ["放弃"]),
        ("Low false negative", 45, ["失标"]),
        ("Low true negative", 20, ["不相关"]),
    ]
    for index, (title, score, verdicts) in enumerate(examples, start=1):
        notice_id, _ = store.upsert_notice(Notice(
            title=title,
            url=f"https://example.invalid/{index}",
            source="fixture",
            published_at=f"2026-07-{index:02d}",
        ))
        store.save_score(notice_id, score_result(score))
        for verdict in verdicts:
            store.add_feedback(notice_id, verdict, "private note must never be selected")
    return store


def test_calibration_metrics_recommendation_bands_and_safe_examples():
    rows = [
        {"notice_id": 1, "title": "High false positive", "score": 90, "verdict": "不相关"},
        {"notice_id": 2, "title": "High true positive", "score": 80, "verdict": "已跟进"},
        {"notice_id": 3, "title": "Ambiguous", "score": 60, "verdict": "放弃"},
        {"notice_id": 4, "title": "Low false negative", "score": 45, "verdict": "失标"},
        {"notice_id": 5, "title": "Low true negative", "score": 20, "verdict": "不相关"},
    ]

    report = build_calibration_report(rows, threshold=50)

    assert report["feedback_count"] == 5
    assert report["labeled_count"] == 4
    assert report["positive_count"] == 2
    assert report["negative_count"] == 2
    assert report["ignored_count"] == 1
    assert report["current_metrics"] == {
        "true_positives": 1,
        "false_positives": 1,
        "true_negatives": 1,
        "false_negatives": 1,
        "precision": 0.5,
        "recall": 0.5,
        "specificity": 0.5,
        "f1": 0.5,
        "accuracy": 0.5,
    }
    assert report["recommended_threshold"] == 45
    assert report["recommended_metrics"]["f1"] == 0.8
    assert report["false_positives"] == [
        {"notice_id": 1, "title": "High false positive", "score": 90, "verdict": "不相关"}
    ]
    assert report["false_negatives"][0]["notice_id"] == 4
    assert next(band for band in report["score_bands"] if band["label"] == "80-100")["positive_rate"] == 0.5
    assert any("preliminary" in warning for warning in report["warnings"])


def test_store_uses_only_latest_feedback_and_never_returns_notes(tmp_path):
    store = seed_calibration_store(tmp_path / "bids.db")

    rows = store.calibration_rows()

    assert len(rows) == 5
    high = next(row for row in rows if row["title"] == "High false positive")
    assert high["verdict"] == "不相关"
    assert all("note" not in row for row in rows)
    assert "private note" not in json.dumps(rows, ensure_ascii=False)


def test_cli_calibrate_outputs_stable_json_and_markdown_file(tmp_path, capsys):
    database = tmp_path / "bids.db"
    seed_calibration_store(database)

    assert main(["--db", str(database), "calibrate", "--threshold", "50", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["recommended_threshold"] == 45
    assert payload["current_metrics"]["false_positives"] == 1
    assert "private note" not in json.dumps(payload)

    output = tmp_path / "calibration.md"
    assert main(["--db", str(database), "calibrate", "--threshold", "50", "--output", str(output)]) == 0
    assert "Calibration report generated" in capsys.readouterr().out
    markdown = output.read_text(encoding="utf-8")
    assert "# OpenBid Intel scoring calibration" in markdown
    assert "Best observed F1 threshold: **45**" in markdown
    assert "private note" not in markdown


def test_empty_and_single_class_reports_warn_without_crashing():
    empty = build_calibration_report([], threshold=50)
    assert empty["recommended_threshold"] is None
    assert "No comparable relevance feedback" in render_calibration_markdown(empty)

    positive_only = build_calibration_report([
        {"notice_id": 1, "title": "Relevant", "score": 70, "verdict": "相关"}
    ])
    assert any("No negative" in warning for warning in positive_only["warnings"])


def test_markdown_escapes_table_cells_and_counts_unknown_verdicts():
    report = build_calibration_report([
        {"notice_id": 1, "title": "Line one|line two\ncontinued", "score": 80, "verdict": "manual|review"},
    ])

    markdown = render_calibration_markdown(report)

    assert report["ignored_count"] == 1
    assert report["verdict_counts"] == {"manual|review": 1}
    assert "manual\\|review" in markdown
    assert "Line one" not in markdown  # ignored rows are never exposed as error examples


@pytest.mark.parametrize("value", ["-1", "101", "not-a-number"])
def test_cli_rejects_invalid_thresholds(tmp_path, value):
    with pytest.raises(SystemExit) as error:
        main(["--db", str(tmp_path / "bids.db"), "calibrate", "--threshold", value])

    assert error.value.code == 2
