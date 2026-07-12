from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from .htmlutil import html_to_text, meta_content
from .models import Notice

USER_AGENT = "BidIntelAgent/0.2 (+local sales intelligence; respectful public-page fetcher)"


@dataclass(slots=True)
class CollectResult:
    source_id: str
    source_name: str
    fetched: int
    notices: list[Notice]
    error: str = ""
    warning: str = ""


def load_sources(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def collect_sources(
    config_path: str | Path, *, fetch_details: bool = True, max_details: int | None = None,
    max_pages: int | None = None, history_days: int | None = None,
) -> list[CollectResult]:
    config = load_sources(config_path)
    interval = float(config.get("request_interval_seconds", 1.0))
    detail_budget = int(max_details if max_details is not None else config.get("max_detail_fetches", 30))
    default_pages = int(max_pages if max_pages is not None else config.get("max_pages", 1))
    default_days = int(history_days if history_days is not None else config.get("history_days", 0))
    priority_terms = [str(term).lower() for term in config.get("priority_detail_terms", [])]
    results: list[CollectResult] = []
    enabled_sources = [source for source in config.get("sources", []) if source.get("enabled", True)]
    source_count = len(enabled_sources)
    base_budget, extra_budget = divmod(max(0, detail_budget), max(1, source_count))
    detail_budgets = [base_budget + (1 if index < extra_budget else 0) for index in range(source_count)]
    reference = datetime.now().astimezone()

    for source_index, source in enumerate(enabled_sources):
        source_detail_budget = detail_budgets[source_index]
        try:
            if source.get("type") != "ccgp_list":
                raise ValueError(f"\u4e0d\u652f\u6301\u7684\u6570\u636e\u6e90\u7c7b\u578b: {source.get('type')}")
            source_pages = int(max_pages if max_pages is not None else source.get("max_pages", default_pages))
            source_days = int(history_days if history_days is not None else source.get("history_days", default_days))
            cutoff = reference - timedelta(days=source_days) if source_days > 0 else None
            notices: list[Notice] = []
            seen_urls: set[str] = set()

            for page_number, page_url in enumerate_ccgp_page_urls(str(source["url"]), source_pages):
                if page_number > 0:
                    time.sleep(interval)
                html_text = fetch_text(page_url)
                page_notices = parse_ccgp_list(
                    html_text, page_url, str(source.get("name", "\u672a\u547d\u540d\u6570\u636e\u6e90")),
                    str(source.get("stage", "\u672a\u77e5\u9636\u6bb5")),
                )
                if not page_notices:
                    break
                oldest = None
                for notice in page_notices:
                    published = _as_datetime(notice.published_at)
                    if published and (oldest is None or published < oldest):
                        oldest = published
                    if cutoff and published and published < cutoff:
                        continue
                    if notice.url not in seen_urls:
                        notices.append(notice)
                        seen_urls.add(notice.url)
                if cutoff and oldest and oldest < cutoff:
                    break

            detail_errors: list[str] = []
            if fetch_details and source_detail_budget > 0:
                candidates = [notice for notice in notices if is_candidate(notice, priority_terms)]
                if "\u4e2d\u6807" in str(source.get("stage", "")) or "\u6210\u4ea4" in str(source.get("stage", "")):
                    candidates = notices
                candidates.sort(key=lambda notice: detail_priority(notice, priority_terms), reverse=True)
                source_details = 0
                for notice in candidates:
                    if source_details >= source_detail_budget:
                        break
                    time.sleep(interval)
                    try:
                        detail_html = fetch_text(notice.url)
                        enrich_ccgp_detail(notice, detail_html)
                    except Exception as exc:
                        detail_errors.append(f"{notice.url}: {exc}")
                    source_details += 1
            warning = ""
            if detail_errors:
                warning = f"\u8be6\u60c5\u8bfb\u53d6\u5931\u8d25 {len(detail_errors)} \u6761\uff1b" + " | ".join(detail_errors[:3])
            results.append(CollectResult(
                str(source["id"]), str(source.get("name", source["id"])), len(notices), notices, warning=warning
            ))
        except Exception as exc:  # Keep other sources running.
            results.append(CollectResult(
                str(source.get("id", "unknown")), str(source.get("name", "unknown")), 0, [], str(exc)
            ))
    return results


def enumerate_ccgp_page_urls(base_url: str, max_pages: int) -> list[tuple[int, str]]:
    pages = max(1, max_pages)
    normalized = base_url if base_url.endswith("/") else base_url + "/"
    return [(0, normalized)] + [
        (index, urljoin(normalized, f"index_{index}.htm")) for index in range(1, pages)
    ]


def fetch_text(url: str, timeout: float = 30.0) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read()
            content_type = response.headers.get_content_charset()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}: {url}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"访问失败: {url}: {exc.reason}") from exc
    return decode_html(payload, content_type)


def decode_html(payload: bytes, declared: str | None = None) -> str:
    candidates = [declared, "utf-8", "gb18030"]
    for encoding in candidates:
        if not encoding:
            continue
        try:
            text = payload.decode(encoding)
            if "\ufffd" not in text:
                return text
        except (LookupError, UnicodeDecodeError):
            pass
    return payload.decode("utf-8", errors="replace")


def repair_mojibake(text: str) -> str:
    if "å" not in text and "ä" not in text and "æ" not in text:
        return text
    try:
        repaired = text.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text
    return repaired if _chinese_count(repaired) > _chinese_count(text) else text


def parse_ccgp_list(html_text: str, base_url: str, source_name: str, stage: str) -> list[Notice]:
    html_text = repair_mojibake(html_text)
    pattern = re.compile(
        r'<li>\s*<a\s+href=["\'](?P<href>[^"\']+)["\'][^>]*title=["\'](?P<title>.*?)["\'][^>]*>.*?</a>\s*'
        r'发布时间：<em>(?P<published>.*?)</em>\s*地域：<em>(?P<region>.*?)</em>\s*采购人：<em>(?P<buyer>.*?)</em>\s*</li>',
        flags=re.IGNORECASE | re.DOTALL,
    )
    notices: list[Notice] = []
    for match in pattern.finditer(html_text):
        values = {key: html_to_text(value) for key, value in match.groupdict().items() if key != "href"}
        notices.append(Notice(
            title=values["title"], url=urljoin(base_url, match.group("href")), source=source_name,
            published_at=_normalize_datetime(values["published"]), stage=stage,
            buyer=values["buyer"], region=values["region"], content=values["title"],
            raw={"list_url": base_url},
        ))
    return notices


def enrich_ccgp_detail(notice: Notice, html_text: str) -> Notice:
    html_text = repair_mojibake(html_text)
    body_match = re.search(r'<div\s+class=["\']vF_detail_content_container["\'][^>]*>(.*?)</div>\s*</div>\s*<!--vF_detail_content_container-->', html_text, re.I | re.S)
    body = html_to_text(body_match.group(1) if body_match else html_text)
    title = meta_content(html_text, "ArticleTitle") or notice.title
    published = meta_content(html_text, "PubDate") or notice.published_at
    buyer = _field(body, "采购单位") or notice.buyer
    region = _field(body, "行政区域") or notice.region
    budget = _extract_budget(body)
    deadline = _extract_deadline(body)
    project_id = _first_match(body, [r"项目编号[：:]\s*([^\s]+)", r"采购项目编号[：:]\s*([^\s]+)"])
    award_supplier = _extract_award_supplier(body)
    award_amount = _extract_award_amount(body)
    notice.title = title
    notice.published_at = _normalize_datetime(published)
    notice.buyer = buyer
    notice.region = region
    notice.budget_cny = budget if budget is not None else notice.budget_cny
    notice.deadline_at = deadline or notice.deadline_at
    notice.project_id = project_id
    notice.award_supplier = award_supplier or notice.award_supplier
    notice.award_amount_cny = award_amount if award_amount is not None else notice.award_amount_cny
    notice.content = body[:50000]
    notice.raw.update({"detail_fetched_at": datetime.now().astimezone().isoformat(), "detail_length": len(body)})
    return notice


INDUSTRY_DETAIL_TERMS = (
    "\u7535\u78c1", "\u5929\u7ebf", "\u5c04\u9891", "\u5fae\u6ce2", "\u76f8\u63a7\u9635", "\u96f7\u8fbe", "\u4eff\u771f", "\u6d4b\u8bd5", "\u6d4b\u91cf", "\u6821\u51c6", "cae",
    "\u8fd1\u573a", "\u8fdc\u573a", "\u7d27\u7f29\u573a", "\u6563\u5c04\u6d4b\u91cf", "\u5fae\u6ce2\u6697\u5ba4", "\u536b\u661f", "\u822a\u5929\u5668", "\u76f8\u4f4d", "\u5e45\u76f8", "\u6d4b\u63a7",
)
SOUTHWEST_TERMS = ("\u56db\u5ddd", "\u91cd\u5e86", "\u4e91\u5357", "\u8d35\u5dde", "\u897f\u85cf")


def is_candidate(notice: Notice, priority_terms: list[str] | None = None) -> bool:
    text = (notice.title + " " + notice.buyer + " " + notice.region).lower()
    return any(term in text for term in INDUSTRY_DETAIL_TERMS) or any(term in text for term in (priority_terms or []))


def detail_priority(notice: Notice, priority_terms: list[str] | None = None) -> int:
    text = (notice.title + " " + notice.buyer + " " + notice.region).lower()
    priority_hits = sum(1 for term in (priority_terms or []) if term in text)
    industry_hits = sum(1 for term in INDUSTRY_DETAIL_TERMS if term in text)
    southwest_hits = sum(1 for term in SOUTHWEST_TERMS if term in text)
    return priority_hits * 100 + industry_hits * 10 + southwest_hits * 5


def _as_datetime(value: str) -> datetime | None:
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed


def _extract_award_supplier(text: str) -> str:
    labels = (
        "\u4e2d\u6807\uff08\u6210\u4ea4\uff09\u4f9b\u5e94\u5546\u540d\u79f0",
        "\u4e2d\u6807\u4f9b\u5e94\u5546\u540d\u79f0", "\u6210\u4ea4\u4f9b\u5e94\u5546\u540d\u79f0",
        "\u4f9b\u5e94\u5546\u540d\u79f0", "\u4e2d\u6807\u4eba", "\u6210\u4ea4\u4eba",
    )
    for label in labels:
        patterns = (
            rf"{label}\s*[\uff1a:]?\s*([^\n\uff1b;]{{2,200}})",
            rf"{label}\s*\n\s*([^\n]{{2,200}})",
        )
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                value = _clean_supplier(match.group(1))
                if value:
                    return value
    return ""


def _clean_supplier(value: str) -> str:
    value = re.split(
        r"(?:\u4f9b\u5e94\u5546\u5730\u5740|\u4e2d\u6807\u91d1\u989d|\u6210\u4ea4\u91d1\u989d|\u8bc4\u5ba1\u603b\u5f97\u5206|\u7edf\u4e00\u793e\u4f1a\u4fe1\u7528\u4ee3\u7801)", value
    )[0]
    value = value.strip(" \uff1a:,\uff0c\u3002;\uff1b\t")
    if value in {"\u8be6\u89c1\u516c\u544a\u6b63\u6587", "\u8be6\u89c1\u9644\u4ef6", "\u65e0"}:
        return ""
    return value[:200]


def _extract_award_amount(text: str) -> float | None:
    patterns = [
        (r"(?:\u4e2d\u6807|\u6210\u4ea4)(?:\u91d1\u989d|\u4ef7|\u603b\u4ef7)\s*[\uff1a:]?\s*[\uffe5\u00a5]?\s*([0-9,.]+)\s*\u4e07\u5143", 10000),
        (r"(?:\u4e2d\u6807|\u6210\u4ea4)(?:\u91d1\u989d|\u4ef7|\u603b\u4ef7)\s*[\uff1a:]?\s*[\uffe5\u00a5]?\s*([0-9,.]+)\s*\u5143", 1),
    ]
    for pattern, multiplier in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return float(match.group(1).replace(",", "")) * multiplier
    return None


def _extract_budget(text: str) -> float | None:
    patterns = [
        r"预算金额\s*[：:]?\s*[￥¥]?\s*([0-9,.]+)\s*万元",
        r"预算金额\s*[：:]?\s*[￥¥]?\s*([0-9,.]+)\s*元",
        r"采购预算\s*[：:]?\s*[￥¥]?\s*([0-9,.]+)\s*万元",
        r"最高限价[^0-9]{0,20}([0-9,.]+)\s*万元",
    ]
    for index, pattern in enumerate(patterns):
        match = re.search(pattern, text, re.I)
        if match:
            value = float(match.group(1).replace(",", ""))
            return value * 10000 if index in {0, 2, 3} else value
    return None


def _extract_deadline(text: str) -> str | None:
    labels = ("提交投标文件截止时间", "响应文件提交截止时间", "投标截止时间", "开标时间", "响应文件开启时间")
    for label in labels:
        match = re.search(rf"{label}\s*[：:]?\s*(20\d{{2}}年\d{{1,2}}月\d{{1,2}}日(?:\s+\d{{1,2}}[:：]\d{{2}})?)", text)
        if match:
            return _normalize_datetime(match.group(1))
    return None


def _field(text: str, label: str) -> str:
    match = re.search(rf"(?:^|\n){label}\s*\n?([^\n]{{1,200}})", text)
    return match.group(1).strip() if match else ""


def _first_match(text: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return ""


def _normalize_datetime(value: str) -> str:
    normalized = value.strip().replace("年", "-").replace("月", "-").replace("日", " ").replace("：", ":")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(normalized, fmt).astimezone()
            return parsed.isoformat(timespec="minutes")
        except ValueError:
            pass
    return value.strip()


def _chinese_count(value: str) -> int:
    return sum("\u4e00" <= char <= "\u9fff" for char in value)
