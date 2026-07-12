from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

UNKNOWN = "\u5f85\u786e\u8ba4"
SEP = "\u3001"
ROLE_UNKNOWN = "\u5f85\u6838\u9a8c"


def load_profile(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)



def resolve_buyer_aliases(profile: dict[str, Any], buyer_query: str) -> tuple[str, list[str]]:
    query = buyer_query.strip()
    if not query:
        return "", []
    for account in profile.get("sales_profile", {}).get("priority_accounts", []):
        name = str(account.get("name") or "").strip()
        aliases = [str(item).strip() for item in account.get("aliases", []) if str(item).strip()]
        candidates = [name, *aliases]
        if any(query.lower() in item.lower() or item.lower() in query.lower() for item in candidates if item):
            unique = list(dict.fromkeys(item for item in candidates if item))
            return name or query, unique
    return query, [query]

def analyze_awards(history: list[dict], profile: dict[str, Any], *, relevant_only: bool = True, product_line: str = "") -> list[dict]:
    analyzed: list[dict] = []
    query = product_line.strip().lower()
    for source in history:
        row = dict(source)
        text = " ".join(str(row.get(key) or "") for key in ("title", "content", "buyer")).lower()
        line_matches: list[dict] = []
        for line in profile.get("business_lines", []):
            strong = _hits(text, line.get("strong_terms", []))
            related = _hits(text, line.get("related_terms", []))
            if strong or related:
                confidence = min(100, len(strong) * 35 + len(related) * 10)
                line_matches.append({
                    "id": str(line.get("id", "")),
                    "name": str(line.get("name", "")),
                    "strong_hits": strong,
                    "related_hits": related,
                    "confidence": confidence,
                })
        line_matches.sort(key=lambda item: item["confidence"], reverse=True)
        row["line_matches"] = line_matches
        row["business_lines"] = [item["name"] for item in line_matches]
        row["relevance"] = _relevance(line_matches)
        row["supplier_role"], row["role_basis"] = infer_supplier_role(
            str(row.get("award_supplier") or ""), text, line_matches
        )
        if relevant_only and not line_matches:
            continue
        if query and not any(query == item["id"].lower() or query in item["name"].lower() for item in line_matches):
            continue
        analyzed.append(row)
    return analyzed


def summarize_suppliers(awards: list[dict], limit: int = 30) -> list[dict]:
    grouped: dict[str, dict] = {}
    for row in awards:
        supplier = str(row.get("award_supplier") or "").strip()
        if not supplier:
            continue
        item = grouped.setdefault(supplier, {
            "supplier": supplier, "award_count": 0, "total_award_cny": 0.0,
            "known_amount_count": 0, "buyers": set(), "business_lines": set(),
            "roles": defaultdict(int), "latest_award": "",
        })
        item["award_count"] += 1
        amount = row.get("award_amount_cny")
        if amount is not None:
            item["total_award_cny"] += float(amount)
            item["known_amount_count"] += 1
        if row.get("buyer"):
            item["buyers"].add(row["buyer"])
        item["business_lines"].update(row.get("business_lines", []))
        item["roles"][row.get("supplier_role", ROLE_UNKNOWN)] += 1
        item["latest_award"] = max(item["latest_award"], str(row.get("published_at") or ""))
    result: list[dict] = []
    for item in grouped.values():
        roles = sorted(item.pop("roles").items(), key=lambda pair: pair[1], reverse=True)
        item["supplier_role"] = roles[0][0] if roles else ROLE_UNKNOWN
        item["buyers"] = sorted(item["buyers"])
        item["business_lines"] = sorted(item["business_lines"])
        result.append(item)
    result.sort(key=lambda item: (item["award_count"], item["total_award_cny"]), reverse=True)
    return result[:limit]


def build_relationships(awards: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str, str], dict] = {}
    for row in awards:
        buyer = str(row.get("buyer") or UNKNOWN)
        supplier = str(row.get("award_supplier") or UNKNOWN)
        lines = row.get("business_lines") or [UNKNOWN]
        for line in lines:
            key = buyer, line, supplier
            item = grouped.setdefault(key, {
                "buyer": buyer, "business_line": line, "supplier": supplier,
                "award_count": 0, "total_award_cny": 0.0, "known_amount_count": 0,
                "latest_award": "", "supplier_role": row.get("supplier_role", ROLE_UNKNOWN),
            })
            item["award_count"] += 1
            if row.get("award_amount_cny") is not None:
                item["total_award_cny"] += float(row["award_amount_cny"])
                item["known_amount_count"] += 1
            item["latest_award"] = max(item["latest_award"], str(row.get("published_at") or ""))
    result = list(grouped.values())
    result.sort(key=lambda item: (item["award_count"], item["total_award_cny"]), reverse=True)
    return result


def infer_supplier_role(supplier: str, text: str, line_matches: list[dict]) -> tuple[str, str]:
    service_terms = ("\u670d\u52a1", "\u7269\u4e1a", "\u7ba1\u7406", "\u54a8\u8be2", "\u8bbe\u8ba1\u9662", "\u68c0\u6d4b", "\u8ba4\u8bc1", "\u8fd0\u7ef4")
    integrator_terms = ("\u5546\u8d38", "\u8d38\u6613", "\u79d1\u6280", "\u7cfb\u7edf", "\u5de5\u7a0b", "\u7535\u5b50", "\u4fe1\u606f", "\u6280\u672f")
    maker_terms = ("\u4eea\u5668", "\u4eea\u8868", "\u8bbe\u5907", "\u5236\u9020", "\u6d4b\u63a7", "\u8f6f\u4ef6", "\u4eff\u771f", "\u5929\u7ebf", "\u5fae\u6ce2")
    if any(term in supplier for term in service_terms):
        return "\u7591\u4f3c\u670d\u52a1\u5546", "\u4f9b\u5e94\u5546\u540d\u79f0\u542b\u670d\u52a1\u7c7b\u8bcd\u6c47\uff0c\u9700\u4eba\u5de5\u6838\u9a8c"
    if line_matches and any(term in supplier for term in maker_terms):
        return "\u7591\u4f3c\u8bbe\u5907/\u8f6f\u4ef6\u5382\u5546", "\u4e1a\u52a1\u76f8\u5173\u4e14\u540d\u79f0\u542b\u4ea7\u54c1\u6216\u5236\u9020\u7c7b\u8bcd\u6c47"
    if line_matches and any(term in supplier for term in integrator_terms):
        return "\u7591\u4f3c\u96c6\u6210/\u7ecf\u9500\u670d\u52a1\u5546", "\u4e1a\u52a1\u76f8\u5173\u4e14\u540d\u79f0\u542b\u79d1\u6280\u3001\u7cfb\u7edf\u6216\u5de5\u7a0b\u7c7b\u8bcd\u6c47"
    if "\u670d\u52a1" in text and not line_matches:
        return "\u7591\u4f3c\u670d\u52a1\u5546", "\u516c\u544a\u4e3b\u8981\u63cf\u8ff0\u670d\u52a1\uff0c\u4e14\u672a\u547d\u4e2d\u4ea7\u54c1\u7ebf"
    return ROLE_UNKNOWN, "\u4ec5\u51ed\u516c\u544a\u548c\u4f9b\u5e94\u5546\u540d\u79f0\u65e0\u6cd5\u7a33\u59a5\u5224\u5b9a\uff0c\u9700\u4eba\u5de5\u6838\u9a8c"


def render_competitor_report(
    summary: list[dict], history: list[dict], buyer_query: str = "", relationships: list[dict] | None = None,
    relevant_only: bool = True, product_line: str = "",
) -> str:
    scope = f"\u6307\u5b9a\u5ba2\u6237\u3010{buyer_query}\u3011" if buyer_query else "\u5168\u90e8\u5ba2\u6237"
    if relevant_only:
        scope += "\uff0c\u4ec5\u7edf\u8ba1\u970d\u83b1\u6c83\u4ea7\u54c1\u7ebf\u76f8\u5173\u516c\u544a"
    if product_line:
        scope += f"\uff0c\u4ea7\u54c1\u7ebf\u3010{product_line}\u3011"
    lines = [
        "# \u970d\u83b1\u6c83\u7ade\u4e89\u60c5\u62a5\u62a5\u544a", "",
        f"- \u751f\u6210\u65f6\u95f4\uff1a{datetime.now().astimezone().isoformat(timespec='minutes')}",
        f"- \u5206\u6790\u8303\u56f4\uff1a{scope}",
        "- \u58f0\u660e\uff1a\u4f9b\u5e94\u5546\u89d2\u8272\u662f\u542f\u53d1\u5f0f\u521d\u5224\uff0c\u4e0d\u662f\u4e8b\u5b9e\u7ed3\u8bba\uff1b\u4e2d\u6807\u4f9b\u5e94\u5546\u4e5f\u4e0d\u5fc5\u7136\u662f\u970d\u83b1\u6c83\u7684\u76f4\u63a5\u7ade\u4e89\u5bf9\u624b\u3002", "",
        "## \u76f8\u5173\u4f9b\u5e94\u5546\u6982\u89c8", "",
    ]
    if not summary:
        lines.append("\u5f53\u524d\u6570\u636e\u4e2d\u6ca1\u6709\u627e\u5230\u7b26\u5408\u8303\u56f4\u7684\u4ea7\u54c1\u7ebf\u76f8\u5173\u4e2d\u6807\u516c\u544a\u3002")
    else:
        lines.extend(["| \u5e8f\u53f7 | \u4f9b\u5e94\u5546 | \u89d2\u8272\u521d\u5224 | \u4e2d\u6807\u6b21\u6570 | \u5df2\u77e5\u603b\u91d1\u989d | \u4ea7\u54c1\u7ebf | \u5ba2\u6237 |", "|---:|---|---|---:|---:|---|---|"])
        for index, row in enumerate(summary, 1):
            lines.append(
                f"| {index} | {row['supplier']} | {row['supplier_role']} | {row['award_count']} | "
                f"{_money(row['total_award_cny']) if row['known_amount_count'] else UNKNOWN} | "
                f"{SEP.join(row['business_lines']) or UNKNOWN} | {SEP.join(row['buyers']) or UNKNOWN} |"
            )
    lines.extend(["", "## \u5ba2\u6237\u2014\u4ea7\u54c1\u7ebf\u2014\u4f9b\u5e94\u5546\u5173\u7cfb", ""])
    rels = relationships or []
    if rels:
        lines.extend(["| \u5ba2\u6237 | \u4ea7\u54c1\u7ebf | \u4f9b\u5e94\u5546 | \u89d2\u8272\u521d\u5224 | \u6b21\u6570 | \u5df2\u77e5\u91d1\u989d | \u6700\u65b0\u65e5\u671f |", "|---|---|---|---|---:|---:|---|"])
        for row in rels[:100]:
            amount = _money(row["total_award_cny"]) if row["known_amount_count"] else UNKNOWN
            lines.append(f"| {row['buyer']} | {row['business_line']} | {row['supplier']} | {row['supplier_role']} | {row['award_count']} | {amount} | {row['latest_award'] or UNKNOWN} |")
    else:
        lines.append("\u5f53\u524d\u65e0\u53ef\u5c55\u793a\u7684\u5173\u7cfb\u6570\u636e\u3002")
    lines.extend(["", "## \u4e2d\u6807\u516c\u544a\u660e\u7ec6", ""])
    for row in history:
        hit_text = []
        for match in row.get("line_matches", []):
            terms = (match.get("strong_hits") or []) + (match.get("related_hits") or [])
            hit_text.append(f"{match['name']}\uff08{SEP.join(terms[:6])}\uff09")
        lines.extend([
            f"### {row['title']}", "", f"- \u91c7\u8d2d\u5355\u4f4d\uff1a{row.get('buyer') or UNKNOWN}",
            f"- \u4e2d\u6807\u4f9b\u5e94\u5546\uff1a{row.get('award_supplier') or UNKNOWN}",
            f"- \u89d2\u8272\u521d\u5224\uff1a{row.get('supplier_role', ROLE_UNKNOWN)}\uff1b{row.get('role_basis', '')}",
            f"- \u4ea7\u54c1\u7ebf\u4f9d\u636e\uff1a{SEP.join(hit_text) or UNKNOWN}",
            f"- \u4e2d\u6807\u91d1\u989d\uff1a{_money(row.get('award_amount_cny'))}",
            f"- \u5730\u533a\uff1a{row.get('region') or UNKNOWN}", f"- \u53d1\u5e03\u65e5\u671f\uff1a{row.get('published_at') or UNKNOWN}",
            f"- \u539f\u6587\uff1a{row.get('url') or UNKNOWN}", "",
        ])
    return "\n".join(lines) + "\n"


def write_competitor_report(path: str | Path, summary: list[dict], history: list[dict], buyer_query: str = "", **kwargs: Any) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_competitor_report(summary, history, buyer_query, **kwargs), encoding="utf-8")
    return target


def _hits(text: str, terms: list[str]) -> list[str]:
    return [str(term) for term in terms if str(term).lower() in text]


def _relevance(line_matches: list[dict]) -> str:
    if not line_matches:
        return "\u4e0d\u76f8\u5173"
    confidence = line_matches[0]["confidence"]
    return "\u9ad8\u76f8\u5173" if confidence >= 45 else "\u53ef\u80fd\u76f8\u5173"


def _money(value: float | None) -> str:
    if value is None:
        return UNKNOWN
    return f"{value / 10000:,.1f} \u4e07\u5143"
