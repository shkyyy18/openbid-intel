from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class Notice:
    title: str
    url: str
    source: str
    published_at: str
    content: str = ""
    deadline_at: str | None = None
    stage: str = "未知"
    buyer: str = ""
    region: str = ""
    budget_cny: float | None = None
    project_id: str = ""
    award_supplier: str = ""
    award_amount_cny: float | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, item: dict[str, Any]) -> "Notice":
        budget = item.get("budget_cny")
        return cls(
            title=str(item.get("title", "")).strip(),
            url=str(item.get("url", "")).strip(),
            source=str(item.get("source", "未知来源")).strip(),
            published_at=str(item.get("published_at", "")).strip(),
            content=str(item.get("content", "")).strip(),
            deadline_at=_optional_text(item.get("deadline_at")),
            stage=str(item.get("stage", "未知")).strip() or "未知",
            buyer=str(item.get("buyer", "")).strip(),
            region=str(item.get("region", "")).strip(),
            budget_cny=float(budget) if budget not in (None, "") else None,
            project_id=str(item.get("project_id", "")).strip(),
            award_supplier=str(item.get("award_supplier", "")).strip(),
            award_amount_cny=float(item["award_amount_cny"]) if item.get("award_amount_cny") not in (None, "") else None,
            raw=dict(item),
        )

    def searchable_text(self) -> str:
        return " ".join((self.title, self.content, self.buyer, self.stage)).lower()


@dataclass(slots=True)
class ScoreResult:
    score: int
    level: str
    business_lines: list[str]
    strong_hits: list[str]
    related_hits: list[str]
    buyer_hits: list[str]
    negative_hits: list[str]
    reasons: list[str]
    risks: list[str]
    recommended_actions: list[str]
    priority_account_hits: list[str] = field(default_factory=list)
    region_match: bool = False
    budget_status: str = ""
    contributions: list[dict[str, Any]] = field(default_factory=list)


def _optional_text(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value).strip() or None


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None
