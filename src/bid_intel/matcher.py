from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import Notice, ScoreResult, parse_datetime


class Matcher:
    def __init__(self, profile: dict[str, Any]):
        self.profile = profile

    @classmethod
    def from_file(cls, path: str | Path) -> "Matcher":
        with Path(path).open("r", encoding="utf-8-sig") as handle:
            return cls(json.load(handle))

    def score(self, notice: Notice, now: datetime | None = None) -> ScoreResult:
        text = notice.searchable_text()
        score = 0
        strong_hits: list[str] = []
        related_hits: list[str] = []
        line_hits: list[tuple[str, int, list[str], list[str]]] = []

        for line in self.profile.get("business_lines", []):
            strong = _hits(text, line.get("strong_terms", []))
            related = _hits(text, line.get("related_terms", []))
            if not strong and not related:
                continue
            line_score = 0
            if strong:
                line_score += int(line.get("base_score", 20)) + min(35, 15 * len(strong))
            if related:
                line_score += min(20, 5 * len(related))
            line_hits.append((str(line["name"]), line_score, strong, related))
            strong_hits.extend(strong)
            related_hits.extend(related)

        if line_hits:
            line_hits.sort(key=lambda item: item[1], reverse=True)
            score += line_hits[0][1]
            score += min(18, sum(item[1] for item in line_hits[1:]) // 3)
            if len(line_hits[0][2]) >= 1 and len(line_hits[0][3]) >= 2:
                score += 12
            if len(line_hits[0][2]) >= 2:
                score += 8

        buyer_hits = _hits(text, self.profile.get("buyer_terms", []))
        score += min(12, 3 * len(buyer_hits))
        stage_weight = int(self.profile.get("stage_weights", {}).get(notice.stage, 0))
        score += stage_weight
        procurement_hits = _hits(text, self.profile.get("procurement_terms", []))
        score += min(5, len(procurement_hits))
        negative_hits = _hits(text, self.profile.get("negative_terms", []))
        score -= min(60, 18 * len(negative_hits))

        sales_profile = self.profile.get("sales_profile", {})
        region_terms = sales_profile.get("focus_regions", self.profile.get("focus_regions", []))
        region_text = " ".join((notice.region, notice.buyer, notice.title, notice.content)).lower()
        matched_regions = _hits(region_text, region_terms)
        region_match = bool(matched_regions)
        if region_match:
            score += 10

        priority_account_hits: list[str] = []
        priority_alias_hits: list[str] = []
        account_text = " ".join((notice.buyer, notice.title, notice.content)).lower()
        for account in sales_profile.get("priority_accounts", []):
            aliases = _hits(account_text, account.get("aliases", []))
            if not aliases:
                continue
            priority_account_hits.append(str(account.get("name", aliases[0])))
            priority_alias_hits.extend(aliases)
            score += int(account.get("weight", 25))
        priority_account_hits = _unique(priority_account_hits)
        if len(priority_account_hits) > 1:
            score -= 10 * (len(priority_account_hits) - 1)

        threshold = float(sales_profile.get(
            "minimum_followup_budget_cny", self.profile.get("min_budget_cny", 0)
        ) or 0)
        budget_status = "\u672a\u8bbe\u7f6e\u91d1\u989d\u95e8\u69db"
        risks: list[str] = []
        actions: list[str] = []
        if threshold > 0:
            if notice.budget_cny is None:
                budget_status = f"\u9884\u7b97\u672a\u77e5\uff0c\u5f85\u786e\u8ba4\u662f\u5426\u8fbe\u5230{_money_wan(threshold)}\u4e07\u5143\u95e8\u69db"
                risks.append("\u9884\u7b97\u672a\u77e5\uff0c\u4e0d\u80fd\u6309\u91d1\u989d\u95e8\u69db\u76f4\u63a5\u6392\u9664")
                actions.append("\u4f18\u5148\u67e5\u770b\u516c\u544a\u9644\u4ef6\uff0c\u786e\u8ba4\u9879\u76ee\u9884\u7b97\u6216\u6700\u9ad8\u9650\u4ef7")
            elif notice.budget_cny < threshold:
                budget_status = f"\u4f4e\u4e8e{_money_wan(threshold)}\u4e07\u5143\u8ddf\u8fdb\u95e8\u69db"
                score -= 25
                risks.append(f"\u5df2\u77e5\u9884\u7b97\u4f4e\u4e8e{_money_wan(threshold)}\u4e07\u5143\u6700\u4f4e\u8ddf\u8fdb\u95e8\u69db")
            else:
                budget_status = f"\u8fbe\u5230{_money_wan(threshold)}\u4e07\u5143\u8ddf\u8fdb\u95e8\u69db"
                score += min(8, max(5, int(math.log10(max(notice.budget_cny, 10))) - 1))
        elif notice.budget_cny is not None:
            budget_status = "\u9884\u7b97\u5df2\u77e5"
            score += min(8, max(1, int(math.log10(max(notice.budget_cny, 10))) - 4))

        deadline = parse_datetime(notice.deadline_at)
        reference = now or datetime.now().astimezone()
        if deadline:
            if deadline.tzinfo is None and reference.tzinfo is not None:
                deadline = deadline.replace(tzinfo=reference.tzinfo)
            days = (deadline - reference).total_seconds() / 86400
            if days < -30:
                score = 0
                risks.append("\u9879\u76ee\u5df2\u622a\u6b62\u8d85\u8fc7 30 \u5929\uff0c\u4ec5\u4f5c\u5386\u53f2\u60c5\u62a5")
            elif days < 0:
                score -= 30
                risks.append("\u622a\u6b62\u65f6\u95f4\u5df2\u8fc7")
            elif days <= 3:
                score -= 8
                risks.append(f"\u8ddd\u622a\u6b62\u4e0d\u8db3 {math.ceil(days)} \u5929\uff0c\u54cd\u5e94\u65f6\u95f4\u7d27")
                actions.append("\u8c03\u67e5\u91c7\u8d2d\u5355\u4f4d\u5386\u53f2\u540c\u7c7b\u9879\u76ee\u53ca\u4e2d\u6807\u65b9")
            elif days <= 10:
                risks.append(f"\u8ddd\u622a\u6b62\u7ea6 {math.ceil(days)} \u5929")
                actions.append("\u5efa\u8bae\u89c2\u5bdf\u6216\u6392\u9664\uff0c\u9664\u975e\u5df2\u6709\u5ba2\u6237\u7ebf\u7d22")
        else:
            risks.append("\u5efa\u8bae\u5217\u4e3a\u91cd\u70b9\u5546\u673a\uff0c\u67e5\u770b\u5b8c\u6574\u516c\u544a\u548c\u9644\u4ef6")

        if notice.budget_cny is None and threshold <= 0:
            risks.append("\u672a\u63d0\u53d6\u5230\u91c7\u8d2d\u5355\u4f4d")
        if not notice.buyer:
            risks.append("\u672a\u63d0\u53d6\u5230\u91c7\u8d2d\u5355\u4f4d")

        score = max(0, min(100, score))
        level = _level(score)
        business_lines = [item[0] for item in line_hits]
        reasons: list[str] = []
        if strong_hits:
            reasons.append("\u547d\u4e2d\u6838\u5fc3\u9700\u6c42\uff1a" + "\u3001".join(_unique(strong_hits)[:8]))
        if related_hits:
            reasons.append("\u547d\u4e2d\u76f8\u5173\u80fd\u529b\uff1a" + "\u3001".join(_unique(related_hits)[:8]))
        if buyer_hits:
            reasons.append("\u91c7\u8d2d\u4e3b\u4f53\u7b26\u5408\u76ee\u6807\u753b\u50cf\uff1a" + "\u3001".join(_unique(buyer_hits)[:5]))
        if region_match:
            reasons.append("\u9500\u552e\u533a\u57df\u5339\u914d\uff1a" + "\u3001".join(_unique(matched_regions)))
        if priority_account_hits:
            reasons.append("\u547d\u4e2d\u91cd\u70b9\u5ba2\u6237\uff1a" + "\u3001".join(priority_account_hits))
        if notice.budget_cny is not None and threshold > 0 and notice.budget_cny >= threshold:
            reasons.append(f"\u9879\u76ee\u9884\u7b97\u8fbe\u5230{_money_wan(threshold)}\u4e07\u5143\u8ddf\u8fdb\u95e8\u69db")
        if stage_weight > 0:
            reasons.append(f"\u5f53\u524d\u9636\u6bb5\u4e3a\u201c{notice.stage}\u201d\uff0c\u4ecd\u6709\u524d\u7f6e\u8ddf\u8fdb\u4ef7\u503c")
        if negative_hits:
            reasons.append("\u5b58\u5728\u6392\u9664\u8bcd\uff1a" + "\u3001".join(_unique(negative_hits)[:5]))
        if not reasons:
            reasons.append("\u8c03\u67e5\u91c7\u8d2d\u5355\u4f4d\u5386\u53f2\u540c\u7c7b\u9879\u76ee\u53ca\u4e2d\u6807\u65b9")

        if priority_account_hits and score >= 30:
            actions.insert(0, "\u91cd\u70b9\u5ba2\u6237\u547d\u4e2d\uff0c\u4f18\u5148\u6838\u5b9e\u9879\u76ee\u5f52\u5c5e\u3001\u7ecf\u8d39\u6765\u6e90\u548c\u5185\u90e8\u5173\u7cfb")
        if score >= 75:
            actions.insert(0, "\u5efa\u8bae\u5217\u4e3a\u91cd\u70b9\u5546\u673a\uff0c\u67e5\u770b\u5b8c\u6574\u516c\u544a\u548c\u9644\u4ef6")
        elif score >= 50:
            actions.insert(0, "\u5efa\u8bae\u9500\u552e\u4eba\u5de5\u590d\u6838\u9700\u6c42\u8fb9\u754c\u4e0e\u8d44\u8d28\u6761\u4ef6")
        else:
            actions.insert(0, "\u8c03\u67e5\u91c7\u8d2d\u5355\u4f4d\u5386\u53f2\u540c\u7c7b\u9879\u76ee\u53ca\u4e2d\u6807\u65b9")
        actions.extend(["\u6838\u5bf9\u6280\u672f\u53c2\u6570\u4e0e\u970d\u83b1\u6c83\u73b0\u6709\u4ea7\u54c1/\u6848\u4f8b", "\u8c03\u67e5\u91c7\u8d2d\u5355\u4f4d\u5386\u53f2\u540c\u7c7b\u9879\u76ee\u53ca\u4e2d\u6807\u65b9"])

        return ScoreResult(
            score=score, level=level, business_lines=business_lines,
            strong_hits=_unique(strong_hits), related_hits=_unique(related_hits),
            buyer_hits=_unique(buyer_hits), negative_hits=_unique(negative_hits),
            priority_account_hits=priority_account_hits, region_match=region_match,
            budget_status=budget_status, reasons=reasons, risks=_unique(risks),
            recommended_actions=_unique(actions),
        )


def _hits(text: str, terms: list[str]) -> list[str]:
    return [str(term) for term in terms if str(term).lower() in text]


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _money_wan(value: float) -> str:
    amount = value / 10000
    return f"{amount:,.0f}" if amount.is_integer() else f"{amount:,.1f}"


def _level(score: int) -> str:
    if score >= 75:
        return "\u91cd\u70b9"
    if score >= 50:
        return "\u5173\u6ce8"
    if score >= 30:
        return "\u89c2\u5bdf"
    return "\u4f4e\u76f8\u5173"
