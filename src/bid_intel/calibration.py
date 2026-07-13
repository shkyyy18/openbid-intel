from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


POSITIVE_VERDICTS = {
    "相关", "已跟进", "已投标", "中标", "失标",
    "relevant", "followed up", "bid submitted", "won", "lost",
}
NEGATIVE_VERDICTS = {"不相关", "irrelevant", "not relevant"}
AMBIGUOUS_VERDICTS = {"放弃", "abandoned", "dropped"}
SCORE_BANDS = ((0, 19), (20, 39), (40, 59), (60, 79), (80, 100))


def build_calibration_report(rows: list[dict[str, Any]], threshold: int = 50) -> dict[str, Any]:
    if not 0 <= threshold <= 100:
        raise ValueError("threshold must be between 0 and 100")

    verdict_counts = Counter(str(row.get("verdict") or "").strip() for row in rows)
    labeled: list[dict[str, Any]] = []
    ignored: list[dict[str, Any]] = []
    for source in rows:
        row = dict(source)
        label = _label(row.get("verdict"))
        if label is None:
            ignored.append(row)
            continue
        row["actual_relevant"] = label
        row["score"] = int(row.get("score") or 0)
        labeled.append(row)

    positive_count = sum(1 for row in labeled if row["actual_relevant"])
    negative_count = len(labeled) - positive_count
    current_metrics = _metrics(labeled, threshold)
    recommendation = _recommend_threshold(labeled, positive_count)

    false_positives = [
        _safe_example(row) for row in labeled
        if row["score"] >= threshold and not row["actual_relevant"]
    ]
    false_positives.sort(key=lambda row: (-row["score"], row["notice_id"]))
    false_negatives = [
        _safe_example(row) for row in labeled
        if row["score"] < threshold and row["actual_relevant"]
    ]
    false_negatives.sort(key=lambda row: (row["score"], row["notice_id"]))

    warnings: list[str] = []
    if not labeled:
        warnings.append("No comparable relevance feedback is available yet.")
    elif len(labeled) < 20:
        warnings.append(f"Only {len(labeled)} comparable labels are available; treat threshold recommendations as preliminary.")
    if labeled and positive_count == 0:
        warnings.append("No positive relevance labels are available, so recall and threshold recommendations are not meaningful.")
    if labeled and negative_count == 0:
        warnings.append("No negative relevance labels are available, so precision and false-positive estimates are not meaningful.")
    if ignored:
        warnings.append(f"Ignored {len(ignored)} ambiguous or unsupported verdict(s) when calculating relevance metrics.")

    return {
        "threshold": threshold,
        "feedback_count": len(rows),
        "labeled_count": len(labeled),
        "positive_count": positive_count,
        "negative_count": negative_count,
        "ignored_count": len(ignored),
        "verdict_counts": dict(sorted(verdict_counts.items())),
        "current_metrics": current_metrics,
        "recommended_threshold": recommendation["threshold"] if recommendation else None,
        "recommended_metrics": recommendation["metrics"] if recommendation else None,
        "score_bands": _score_bands(labeled),
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "warnings": warnings,
    }


def render_calibration_markdown(report: dict[str, Any]) -> str:
    metrics = report["current_metrics"]
    lines = [
        "# OpenBid Intel scoring calibration",
        "",
        f"- Feedback records considered: {report['feedback_count']}",
        f"- Comparable relevance labels: {report['labeled_count']}",
        f"- Positive / negative labels: {report['positive_count']} / {report['negative_count']}",
        f"- Ignored ambiguous or unsupported labels: {report['ignored_count']}",
        f"- Evaluated score threshold: {report['threshold']}",
        "",
        "## Threshold metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| True positives | {metrics['true_positives']} |",
        f"| False positives | {metrics['false_positives']} |",
        f"| True negatives | {metrics['true_negatives']} |",
        f"| False negatives | {metrics['false_negatives']} |",
        f"| Precision | {_percent(metrics['precision'])} |",
        f"| Recall | {_percent(metrics['recall'])} |",
        f"| Specificity | {_percent(metrics['specificity'])} |",
        f"| F1 score | {_percent(metrics['f1'])} |",
        f"| Accuracy | {_percent(metrics['accuracy'])} |",
        "",
    ]

    if report["recommended_threshold"] is not None:
        recommended = report["recommended_metrics"]
        lines.extend([
            "## Deterministic threshold recommendation",
            "",
            f"Best observed F1 threshold: **{report['recommended_threshold']}** "
            f"(precision {_percent(recommended['precision'])}, recall {_percent(recommended['recall'])}, "
            f"F1 {_percent(recommended['f1'])}).",
            "",
            "This is descriptive evidence from recorded feedback, not an automatic profile change.",
            "",
        ])

    lines.extend([
        "## Score bands",
        "",
        "| Score band | Labeled | Relevant | Positive rate |",
        "|---|---:|---:|---:|",
    ])
    for band in report["score_bands"]:
        lines.append(
            f"| {band['label']} | {band['count']} | {band['positive_count']} | {_percent(band['positive_rate'])} |"
        )

    lines.extend(["", "## Latest verdict counts", "", "| Verdict | Count |", "|---|---:|"])
    if report["verdict_counts"]:
        for verdict, count in report["verdict_counts"].items():
            lines.append(f"| {_markdown_cell(verdict or '(empty)')} | {count} |")
    else:
        lines.append("| none | 0 |")

    _append_examples(lines, "False positives at the evaluated threshold", report["false_positives"])
    _append_examples(lines, "False negatives at the evaluated threshold", report["false_negatives"])

    if report["warnings"]:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in report["warnings"])
    return "\n".join(lines) + "\n"


def render_calibration_json(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2) + "\n"


def write_calibration_report(path: str | Path, report: dict[str, Any], *, json_output: bool = False) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    content = render_calibration_json(report) if json_output else render_calibration_markdown(report)
    target.write_text(content, encoding="utf-8")
    return target


def _label(verdict: Any) -> bool | None:
    normalized = str(verdict or "").strip().lower()
    if normalized in POSITIVE_VERDICTS:
        return True
    if normalized in NEGATIVE_VERDICTS:
        return False
    if normalized in AMBIGUOUS_VERDICTS:
        return None
    return None


def _metrics(rows: list[dict[str, Any]], threshold: int) -> dict[str, Any]:
    tp = sum(1 for row in rows if row["score"] >= threshold and row["actual_relevant"])
    fp = sum(1 for row in rows if row["score"] >= threshold and not row["actual_relevant"])
    tn = sum(1 for row in rows if row["score"] < threshold and not row["actual_relevant"])
    fn = sum(1 for row in rows if row["score"] < threshold and row["actual_relevant"])
    precision = _ratio(tp, tp + fp)
    recall = _ratio(tp, tp + fn)
    specificity = _ratio(tn, tn + fp)
    accuracy = _ratio(tp + tn, len(rows))
    f1 = _ratio(2 * precision * recall, precision + recall)
    return {
        "true_positives": tp,
        "false_positives": fp,
        "true_negatives": tn,
        "false_negatives": fn,
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "f1": f1,
        "accuracy": accuracy,
    }


def _recommend_threshold(rows: list[dict[str, Any]], positive_count: int) -> dict[str, Any] | None:
    if not rows or not positive_count:
        return None
    candidates = sorted({0, 100, *[int(row["score"]) for row in rows]})
    evaluated = [(threshold, _metrics(rows, threshold)) for threshold in candidates]
    threshold, metrics = max(
        evaluated,
        key=lambda item: (
            item[1]["f1"], item[1]["precision"], item[1]["recall"], item[0]
        ),
    )
    return {"threshold": threshold, "metrics": metrics}


def _score_bands(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bands = []
    for lower, upper in SCORE_BANDS:
        selected = [row for row in rows if lower <= row["score"] <= upper]
        positives = sum(1 for row in selected if row["actual_relevant"])
        bands.append({
            "label": f"{lower}-{upper}",
            "minimum": lower,
            "maximum": upper,
            "count": len(selected),
            "positive_count": positives,
            "positive_rate": _ratio(positives, len(selected)),
        })
    return bands


def _safe_example(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "notice_id": int(row.get("notice_id") or row.get("id") or 0),
        "title": str(row.get("title") or ""),
        "score": int(row.get("score") or 0),
        "verdict": str(row.get("verdict") or ""),
    }


def _append_examples(lines: list[str], heading: str, rows: list[dict[str, Any]]) -> None:
    lines.extend(["", f"## {heading}", ""])
    if not rows:
        lines.append("None.")
        return
    lines.extend(["| Notice ID | Score | Verdict | Title |", "|---:|---:|---|---|"])
    for row in rows:
        title = _markdown_cell(row["title"])
        verdict = _markdown_cell(row["verdict"])
        lines.append(f"| {row['notice_id']} | {row['score']} | {verdict} | {title} |")


def _markdown_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def _ratio(numerator: float, denominator: float) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _percent(value: float) -> str:
    return f"{value * 100:.1f}%"
