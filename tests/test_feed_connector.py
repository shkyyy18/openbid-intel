import json
from datetime import datetime, timezone
from pathlib import Path

from bid_intel.collectors import collect_sources, default_connector_registry
from bid_intel.connectors import ConnectorContext
from bid_intel.feed_connector import RssAtomConnector, parse_rss_atom


FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_rss_feed_fields_and_html_content():
    notices = parse_rss_atom(
        (FIXTURES / "rss_sample.xml").read_text(encoding="utf-8"),
        feed_url="https://example.invalid/feed.xml",
        source_name="Example feed",
        stage="request for proposal",
        region="Global",
    )
    assert len(notices) == 1
    notice = notices[0]
    assert notice.title == "Cloud platform services RFP"
    assert notice.published_at == "2026-07-12T09:30+08:00"
    assert notice.content == "Managed cloud, migration, and security services."
    assert notice.region == "Global"
    assert notice.raw["connector_type"] == "rss_atom"


def test_parse_atom_feed_resolves_relative_link():
    notices = parse_rss_atom(
        (FIXTURES / "atom_sample.xml").read_text(encoding="utf-8"),
        feed_url="https://example.invalid/procurement/feed.atom",
        source_name="Example Atom",
    )
    assert notices[0].url == "https://example.invalid/notices/200"
    assert notices[0].published_at == "2026-07-11T08:00+00:00"


def test_rss_connector_applies_cutoff_and_max_items():
    text = (FIXTURES / "rss_sample.xml").read_text(encoding="utf-8")
    connector = RssAtomConnector()
    context = ConnectorContext(
        fetch_text=lambda _url: text,
        cutoff=datetime(2026, 7, 12, 2, tzinfo=timezone.utc),
    )
    output = connector.collect(
        {"id": "feed", "name": "Feed", "url": "https://example.invalid/feed.xml", "max_items": 1},
        context,
    )
    assert output.notices == []


def test_collect_sources_dispatches_rss_connector(tmp_path, monkeypatch):
    config = {
        "request_interval_seconds": 0,
        "history_days": 0,
        "sources": [{
            "id": "rss-demo",
            "name": "RSS demo",
            "type": "rss_atom",
            "url": "https://example.invalid/feed.xml",
            "stage": "notice",
        }],
    }
    path = tmp_path / "sources.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    text = (FIXTURES / "rss_sample.xml").read_text(encoding="utf-8")
    monkeypatch.setattr("bid_intel.collectors.fetch_text", lambda _url, timeout=30: text)
    result = collect_sources(path, fetch_details=False)[0]
    assert not result.error
    assert result.fetched == 1
    assert result.notices[0].source == "RSS demo"


def test_default_registry_exposes_supported_types():
    assert default_connector_registry().types() == ("ccgp_list", "rss_atom")



def test_feed_does_not_consume_html_detail_budget(tmp_path, monkeypatch):
    config = {
        "request_interval_seconds": 0,
        "max_detail_fetches": 1,
        "sources": [
            {"id": "feed", "name": "Feed", "type": "rss_atom", "url": "https://example.invalid/feed.xml"},
            {"id": "html", "name": "HTML", "type": "ccgp_list", "url": "https://example.invalid/list/", "stage": "\u4e2d\u6807\u516c\u544a"},
        ],
    }
    path = tmp_path / "sources.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    rss = (FIXTURES / "rss_sample.xml").read_text(encoding="utf-8")
    detail_calls = []

    def fake_fetch(url, timeout=30):
        if url.endswith("feed.xml"):
            return rss
        if url.endswith("/list/"):
            return '<li><a href="detail.htm" title="Award notice">x</a>\u53d1\u5e03\u65f6\u95f4\uff1a<em>2026-07-01</em> \u5730\u57df\uff1a<em>West</em> \u91c7\u8d2d\u4eba\uff1a<em>Buyer</em></li>'
        detail_calls.append(url)
        return "<html><body>detail</body></html>"

    monkeypatch.setattr("bid_intel.collectors.fetch_text", fake_fetch)
    results = collect_sources(path, max_details=1, max_pages=1)
    assert not results[1].error
    assert detail_calls == ["https://example.invalid/list/detail.htm"]
