from datetime import datetime

from bid_intel.collectors import (
    collect_sources, detail_priority, enrich_ccgp_detail, enumerate_ccgp_page_urls, is_candidate, parse_ccgp_list,
)
from bid_intel.models import Notice


LIST_HTML = '''
<ul>
<li> <a href="./202607/t20260711_1.htm" target="_blank" title="天线测试系统公开招标公告">天线测试系统公开招标公告</a>
发布时间：<em>2026-07-11 12:30</em> 地域：<em>北京</em> 采购人：<em>某研究院</em>
</li>
</ul>
'''

DETAIL_HTML = '''
<meta name="ArticleTitle" content="天线测试系统公开招标公告" />
<meta name="PubDate" content="2026-07-11 12:30" />
<div class="vF_detail_content_container"><div>
采购项目编号：ABC-123
采购单位
某电子研究院
行政区域
北京市
预算金额：￥320.50万元
提交投标文件截止时间：2026年08月01日 09:30
项目概况：采购微波暗室和天线近场测量系统。
</div></div><!--vF_detail_content_container-->
'''


def test_parse_ccgp_list():
    notices = parse_ccgp_list(LIST_HTML, "https://www.ccgp.gov.cn/cggg/dfgg/gkzb/", "中国政府采购网", "招标公告")
    assert len(notices) == 1
    assert notices[0].buyer == "某研究院"
    assert notices[0].region == "北京"
    assert notices[0].url == "https://www.ccgp.gov.cn/cggg/dfgg/gkzb/202607/t20260711_1.htm"
    assert notices[0].published_at.startswith("2026-07-11T12:30")


def test_enrich_ccgp_detail():
    notice = Notice(title="旧标题", url="u", source="s", published_at="2026-01-01")
    enriched = enrich_ccgp_detail(notice, DETAIL_HTML)
    assert enriched.title == "天线测试系统公开招标公告"
    assert enriched.project_id == "ABC-123"
    assert enriched.budget_cny == 3_205_000
    assert enriched.deadline_at.startswith("2026-08-01T09:30")
    assert "天线近场测量系统" in enriched.content



def test_ccgp_page_urls_follow_index_pattern():
    pages = enumerate_ccgp_page_urls("https://www.ccgp.gov.cn/cggg/dfgg/zbgg/", 3)
    assert pages == [
        (0, "https://www.ccgp.gov.cn/cggg/dfgg/zbgg/"),
        (1, "https://www.ccgp.gov.cn/cggg/dfgg/zbgg/index_1.htm"),
        (2, "https://www.ccgp.gov.cn/cggg/dfgg/zbgg/index_2.htm"),
    ]



def test_priority_account_candidate_ranks_above_generic_candidate():
    terms = ["\u793a\u4f8b\u6280\u672f\u5927\u5b66", "\u793a\u4f8b\u7814\u7a76\u9662"]
    priority = Notice(
        title="\u901a\u7528\u79d1\u7814\u8bbe\u5907\u91c7\u8d2d", url="1", source="s", published_at="2026-07-01",
        buyer="\u793a\u4f8b\u6280\u672f\u5927\u5b66", region="\u56db\u5ddd",
    )
    generic = Notice(
        title="\u5929\u7ebf\u6d4b\u8bd5\u7cfb\u7edf\u91c7\u8d2d", url="2", source="s", published_at="2026-07-01",
        buyer="\u67d0\u7814\u7a76\u9662", region="\u5e7f\u4e1c",
    )
    assert is_candidate(priority, terms)
    assert detail_priority(priority, terms) > detail_priority(generic, terms)


def test_industry_candidate_terms_are_real_chinese_keywords():
    notice = Notice(title="\u5929\u7ebf\u8fd1\u573a\u6d4b\u91cf\u7cfb\u7edf", url="u", source="s", published_at="2026-07-01")
    unrelated = Notice(title="\u529e\u516c\u5bb6\u5177\u91c7\u8d2d", url="v", source="s", published_at="2026-07-01")
    assert is_candidate(notice)
    assert not is_candidate(unrelated)


def test_southwest_region_increases_detail_priority():
    sichuan = Notice(title="\u5929\u7ebf\u6d4b\u8bd5", url="1", source="s", published_at="2026-07-01", region="\u56db\u5ddd")
    beijing = Notice(title="\u5929\u7ebf\u6d4b\u8bd5", url="2", source="s", published_at="2026-07-01", region="\u5317\u4eac")
    assert detail_priority(sichuan) > detail_priority(beijing)


def test_detail_budget_is_global_not_per_source(tmp_path, monkeypatch):
    import json
    config = {
        "request_interval_seconds": 0, "max_detail_fetches": 1,
        "sources": [
            {"id": "a", "name": "A", "type": "ccgp_list", "url": "https://example/a/", "stage": "\u4e2d\u6807\u516c\u544a"},
            {"id": "b", "name": "B", "type": "ccgp_list", "url": "https://example/b/", "stage": "\u4e2d\u6807\u516c\u544a"},
        ],
    }
    path = tmp_path / "sources.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    calls = []
    def fake_fetch(url, timeout=30):
        calls.append(url)
        if url.endswith('/a/') or url.endswith('/b/'):
            key = 'a' if url.endswith('/a/') else 'b'
            return f'<li><a href="detail-{key}.htm" title="\u5929\u7ebf\u6d4b\u8bd5">x</a>\u53d1\u5e03\u65f6\u95f4\uff1a<em>2026-07-01</em> \u5730\u57df\uff1a<em>\u56db\u5ddd</em> \u91c7\u8d2d\u4eba\uff1a<em>\u67d0\u9662</em></li>'
        return '<div>\u4e2d\u6807\u4f9b\u5e94\u5546\u540d\u79f0\uff1a\u67d0\u79d1\u6280\u516c\u53f8</div>'
    monkeypatch.setattr('bid_intel.collectors.fetch_text', fake_fetch)
    results = collect_sources(path, max_details=1, max_pages=1)
    assert len(results) == 2
    assert sum('detail-' in url for url in calls) == 1


def test_detail_failure_keeps_list_notices_and_reports_warning(tmp_path, monkeypatch):
    import json
    config = {"request_interval_seconds": 0, "sources": [{"id": "a", "name": "A", "type": "ccgp_list", "url": "https://example/a/", "stage": "\u4e2d\u6807\u516c\u544a"}]}
    path = tmp_path / "sources.json"; path.write_text(json.dumps(config), encoding="utf-8")
    def fake_fetch(url, timeout=30):
        if url.endswith('/a/'):
            return '<li><a href="detail.htm" title="\u5929\u7ebf\u6d4b\u8bd5">x</a>\u53d1\u5e03\u65f6\u95f4\uff1a<em>2026-07-01</em> \u5730\u57df\uff1a<em>\u56db\u5ddd</em> \u91c7\u8d2d\u4eba\uff1a<em>\u67d0\u9662</em></li>'
        raise RuntimeError('detail unavailable')
    monkeypatch.setattr('bid_intel.collectors.fetch_text', fake_fetch)
    result = collect_sources(path, max_details=1, max_pages=1)[0]
    assert result.error == ""
    assert len(result.notices) == 1
    assert "\u8be6\u60c5\u8bfb\u53d6\u5931\u8d25 1 \u6761" in result.warning
