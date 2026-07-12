from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Notice, ScoreResult


def build_explanation(notice: Notice, result: ScoreResult, profile: str | Path) -> dict[str, Any]:
    return {
        "profile": str(profile),
        "input": {
            "title": notice.title,
            "buyer": notice.buyer,
            "content": notice.content,
            "stage": notice.stage,
            "region": notice.region,
            "budget_cny": notice.budget_cny,
            "published_at": notice.published_at,
            "deadline_at": notice.deadline_at,
        },
        "score": result.score,
        "level": result.level,
        "business_lines": result.business_lines,
        "contributions": result.contributions,
        "hits": {
            "strong": result.strong_hits,
            "related": result.related_hits,
            "buyer": result.buyer_hits,
            "negative": result.negative_hits,
            "priority_accounts": result.priority_account_hits,
        },
        "region_match": result.region_match,
        "budget_status": result.budget_status,
        "reasons": result.reasons,
        "risks": result.risks,
        "recommended_actions": result.recommended_actions,
    }


def render_explanation(payload: dict[str, Any]) -> str:
    lines = [
        f"Score: {payload['score']} ({payload['level']})",
        "Business lines: " + (", ".join(payload["business_lines"]) or "none"),
        "",
        "Score contributions:",
    ]
    contributions = payload.get("contributions", [])
    if contributions:
        for item in contributions:
            points = int(item["points"])
            line = f"  {points:+d}  {item['category']}: {item['label']}"
            if item.get("details"):
                line += f" - {item['details']}"
            lines.append(line)
    else:
        lines.append("  0  No scoring rules matched")

    for heading, key in (
        ("Reasons", "reasons"),
        ("Risks", "risks"),
        ("Recommended actions", "recommended_actions"),
    ):
        lines.extend(["", f"{heading}:"])
        values = payload.get(key, [])
        lines.extend(f"  - {value}" for value in values) if values else lines.append("  - none")
    return "\n".join(lines) + "\n"


def render_explanation_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
