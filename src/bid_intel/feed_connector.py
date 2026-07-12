from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urljoin
from xml.etree import ElementTree

from .connectors import ConnectorContext, ConnectorOutput
from .htmlutil import html_to_text
from .models import Notice


class RssAtomConnector:
    type_name = "rss_atom"
    uses_detail_budget = False

    def collect(self, source: dict[str, Any], context: ConnectorContext) -> ConnectorOutput:
        feed_url = str(source["url"])
        text = context.fetch_text(feed_url)
        notices = parse_rss_atom(
            text,
            feed_url=feed_url,
            source_name=str(source.get("name", source.get("id", "RSS/Atom feed"))),
            stage=str(source.get("stage", "notice")),
            region=str(source.get("region", "")),
            buyer=str(source.get("buyer", "")),
        )
        if context.cutoff:
            notices = [notice for notice in notices if _after_cutoff(notice.published_at, context.cutoff)]
        max_items = int(source.get("max_items", 0))
        if max_items > 0:
            notices = notices[:max_items]
        return ConnectorOutput(_deduplicate(notices))


def parse_rss_atom(
    text: str, *, feed_url: str, source_name: str, stage: str = "notice",
    region: str = "", buyer: str = "",
) -> list[Notice]:
    root = ElementTree.fromstring(text)
    entries = [element for element in root.iter() if _local_name(element.tag) in {"item", "entry"}]
    notices: list[Notice] = []
    for entry in entries:
        title = _child_text(entry, "title")
        url = _entry_url(entry, feed_url)
        published = _normalize_date(
            _child_text(entry, "published", "updated", "pubDate", "date", "dc:date")
        )
        if not title or not url or not published:
            continue
        content = html_to_text(_child_text(entry, "content", "encoded", "description", "summary"))
        notices.append(Notice(
            title=title,
            url=url,
            source=source_name,
            published_at=published,
            content=content,
            stage=stage,
            buyer=buyer,
            region=region,
            raw={"connector_type": "rss_atom", "feed_url": feed_url},
        ))
    return notices


def _entry_url(entry: ElementTree.Element, feed_url: str) -> str:
    for child in entry:
        if _local_name(child.tag) != "link":
            continue
        relation = child.attrib.get("rel", "alternate")
        candidate = child.attrib.get("href") or (child.text or "")
        if candidate.strip() and relation in {"", "alternate"}:
            return urljoin(feed_url, candidate.strip())
    guid = _child_text(entry, "guid", "id")
    return urljoin(feed_url, guid) if guid.startswith(("http://", "https://", "/")) else ""


def _child_text(entry: ElementTree.Element, *names: str) -> str:
    wanted = {name.split(":")[-1] for name in names}
    for child in entry:
        if _local_name(child.tag) in wanted:
            return "".join(child.itertext()).strip()
    return ""


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].rsplit(":", 1)[-1]


def _normalize_date(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    try:
        parsed = parsedate_to_datetime(text)
        if parsed.tzinfo is None:
            parsed = parsed.astimezone()
        return parsed.isoformat(timespec="minutes")
    except (TypeError, ValueError, OverflowError):
        pass
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.astimezone()
        return parsed.isoformat(timespec="minutes")
    except ValueError:
        return text


def _after_cutoff(value: str, cutoff: datetime) -> bool:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return True
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed >= cutoff


def _deduplicate(notices: list[Notice]) -> list[Notice]:
    seen: set[str] = set()
    unique: list[Notice] = []
    for notice in notices:
        if notice.url not in seen:
            unique.append(notice)
            seen.add(notice.url)
    return unique
