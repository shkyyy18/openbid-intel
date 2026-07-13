from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from .matcher import Matcher
from .models import Notice


def build_routing_report(
    notices: list[tuple[int, Notice]],
    profiles: list[dict[str, Any]],
    *,
    min_score: int = 30,
    limit: int = 100,
    top_profiles: int = 3,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    """Score notices against several profiles without modifying stored single-profile scores."""
    if not 0 <= min_score <= 100:
        raise ValueError("min_score must be between 0 and 100")
    if limit < 1:
        raise ValueError("limit must be at least 1")
    if top_profiles < 1:
        raise ValueError("top_profiles must be at least 1")

    prepared = _prepare_profiles(profiles)
    scoring_time = as_of or datetime.now().astimezone()
    routed: list[dict[str, Any]] = []
    matched_count = 0
    for notice_id, notice in notices:
        matches = []
        for item in prepared:
            result = item["matcher"].score(notice, now=scoring_time)
            matches.append({
                "profile_id": item["id"],
                "profile_title": item["title"],
                "score": result.score,
                "level": result.level,
                "business_lines": list(result.business_lines),
                "reasons": list(result.reasons),
                "risks": list(result.risks),
                "recommended_actions": list(result.recommended_actions),
            })
        matches.sort(key=lambda row: (-row["score"], row["profile_id"]))
        if not matches or matches[0]["score"] < min_score:
            continue
        matched_count += 1
        selected = matches[:top_profiles]
        assigned = selected[0]
        routed.append({
            "notice_id": notice_id,
            "title": notice.title,
            "buyer": notice.buyer,
            "region": notice.region,
            "published_at": notice.published_at,
            "deadline_at": notice.deadline_at,
            "url": notice.url,
            "assigned_profile": assigned,
            "alternatives": [
                _compact_match(match) for match in selected[1:]
            ],
        })

    routed.sort(
        key=lambda row: (
            row["assigned_profile"]["score"],
            row["published_at"],
            -row["notice_id"],
        ),
        reverse=True,
    )
    routed = routed[:limit]
    assigned_counts = Counter(row["assigned_profile"]["profile_id"] for row in routed)
    profile_counts = [
        {
            "profile_id": item["id"],
            "profile_title": item["title"],
            "assigned_count": assigned_counts.get(item["id"], 0),
        }
        for item in prepared
    ]
    profile_counts.sort(key=lambda row: (-row["assigned_count"], row["profile_id"]))

    return {
        "profile_count": len(prepared),
        "notice_count": len(notices),
        "matched_notice_count": matched_count,
        "unmatched_notice_count": len(notices) - matched_count,
        "returned_notice_count": len(routed),
        "min_score": min_score,
        "limit": limit,
        "top_profiles": top_profiles,
        "profile_counts": profile_counts,
        "routes": routed,
    }


def render_routing_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# OpenBid Intel multi-profile routing",
        "",
        f"- Profiles evaluated: {report['profile_count']}",
        f"- Notices evaluated: {report['notice_count']}",
        f"- Notices meeting threshold: {report['matched_notice_count']}",
        f"- Notices below threshold: {report['unmatched_notice_count']}",
        f"- Routes returned: {report['returned_notice_count']}",
        f"- Minimum score: {report['min_score']}",
        "",
        "## Assignment summary",
        "",
        "| Profile | Assigned routes |",
        "|---|---:|",
    ]
    for row in report["profile_counts"]:
        label = f"{row['profile_title']} (`{row['profile_id']}`)"
        lines.append(f"| {_cell(label)} | {row['assigned_count']} |")

    lines.extend([
        "",
        "## Routed opportunities",
        "",
    ])
    if not report["routes"]:
        lines.append("No notices met the selected routing threshold.")
        return "\n".join(lines) + "\n"

    for index, row in enumerate(report["routes"], start=1):
        assigned = row["assigned_profile"]
        lines.extend([
            f"### {index}. {_heading(row['title'])}",
            "",
            f"- Notice ID: {row['notice_id']}",
            f"- Assigned profile: **{_inline(assigned['profile_title'])}** (`{_inline(assigned['profile_id'])}`)",
            f"- Score: **{assigned['score']}** ({_inline(assigned['level'])})",
            f"- Buyer: {_inline(row['buyer']) or '-'}",
            f"- Region: {_inline(row['region']) or '-'}",
            f"- Published: {_inline(row['published_at']) or '-'}",
            f"- Deadline: {_inline(row['deadline_at']) or '-'}",
        ])
        if assigned["business_lines"]:
            lines.append(f"- Matched lines: {_inline(', '.join(assigned['business_lines']))}")
        if assigned["reasons"]:
            lines.append(f"- Why: {_inline('; '.join(assigned['reasons']))}")
        if assigned["risks"]:
            lines.append(f"- Risks: {_inline('; '.join(assigned['risks']))}")
        if assigned["recommended_actions"]:
            lines.append(f"- Next actions: {_inline('; '.join(assigned['recommended_actions']))}")
        if row["alternatives"]:
            alternatives = ", ".join(
                f"{item['profile_title']} ({item['score']})" for item in row["alternatives"]
            )
            lines.append(f"- Alternative profiles: {_inline(alternatives)}")
        if _safe_url(row["url"]):
            lines.append(f"- Official notice: <{_safe_link(row['url'])}>")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_routing_json(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2) + "\n"


def write_routing_report(
    path: str | Path,
    report: dict[str, Any],
    *,
    json_output: bool = False,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    content = render_routing_json(report) if json_output else render_routing_markdown(report)
    target.write_text(content, encoding="utf-8")
    return target


def _prepare_profiles(profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prepared = []
    seen: set[str] = set()
    for profile in profiles:
        meta = profile.get("meta", {})
        profile_id = str(meta.get("id") or "").strip()
        if not profile_id:
            raise ValueError("every routing profile must define meta.id")
        if profile_id in seen:
            raise ValueError(f"duplicate routing profile id: {profile_id}")
        seen.add(profile_id)
        prepared.append({
            "id": profile_id,
            "title": str(meta.get("title") or profile_id),
            "matcher": Matcher(profile),
        })
    prepared.sort(key=lambda item: item["id"])
    return prepared


def _compact_match(match: dict[str, Any]) -> dict[str, Any]:
    return {
        "profile_id": match["profile_id"],
        "profile_title": match["profile_title"],
        "score": match["score"],
        "level": match["level"],
        "business_lines": match["business_lines"],
    }


def _cell(value: Any) -> str:
    return _inline(value).replace("|", "\\|")


def _heading(value: Any) -> str:
    return _inline(value).replace("#", "\\#")


def _inline(value: Any) -> str:
    return str(value or "").replace("\r", " ").replace("\n", " ").strip()


def _safe_url(value: Any) -> bool:
    link = _safe_link(value)
    lowered = link.lower()
    return (lowered.startswith("https://") or lowered.startswith("http://")) and not any(
        character.isspace() or character in "<>" for character in link
    )


def _safe_link(value: Any) -> str:
    return str(value or "").strip()
