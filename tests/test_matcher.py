from datetime import datetime

from bid_intel.matcher import Matcher
from bid_intel.models import Notice


def profile():
    return {
        "business_lines": [{
            "id": "measurement", "name": "电磁场测量", "base_score": 25,
            "strong_terms": ["近场测量", "天线测量系统"],
            "related_terms": ["微波暗室", "转台"],
        }],
        "buyer_terms": ["研究院"],
        "procurement_terms": ["采购"],
        "negative_terms": ["物业", "保洁"],
        "stage_weights": {"采购意向": 8, "中标公告": -12},
        "min_budget_cny": 0,
    }


def test_relevant_notice_scores_high():
    notice = Notice(
        title="天线近场测量系统采购意向", url="x", source="test",
        published_at="2026-07-12T00:00:00+08:00", deadline_at="2026-08-10T00:00:00+08:00",
        stage="采购意向", buyer="某研究院", budget_cny=5_000_000,
        content="采购平面近场测量和微波暗室转台。",
    )
    result = Matcher(profile()).score(notice, datetime.fromisoformat("2026-07-12T00:00:00+08:00"))
    assert result.score >= 75
    assert result.level == "重点"
    assert "电磁场测量" in result.business_lines


def test_negative_notice_is_penalized():
    notice = Notice(
        title="园区物业采购", url="x", source="test", published_at="2026-07-12T00:00:00+08:00",
        stage="招标公告", buyer="某园区", content="物业保洁服务",
    )
    result = Matcher(profile()).score(notice)
    assert result.score < 30
    assert set(result.negative_hits) == {"物业", "保洁"}




def sales_profile():
    data = profile()
    data["sales_profile"] = {
        "focus_regions": ["\u56db\u5ddd", "\u91cd\u5e86", "\u4e91\u5357", "\u8d35\u5dde", "\u897f\u85cf"],
        "minimum_followup_budget_cny": 1_000_000,
        "priority_accounts": [
            {"name": "\u793a\u4f8b\u6280\u672f\u5927\u5b66", "aliases": ["\u793a\u4f8b\u6280\u672f\u5927\u5b66", "\u793a\u4f8b\u5927\u5b66"], "weight": 20},
            {"name": "\u793a\u4f8b\u7814\u7a76\u9662", "aliases": ["\u793a\u4f8b\u7814\u7a76\u9662", "\u793a\u4f8b\u7814\u7a76\u9662"], "weight": 28},
            {"name": "\u793a\u4f8b\u5b9e\u9a8c\u5ba4", "aliases": ["\u793a\u4f8b\u5b9e\u9a8c\u5ba4", "\u793a\u4f8b\u5b9e\u9a8c\u5ba4", "\u793a\u4f8b\u5b9e\u9a8c\u5ba4"], "weight": 28},
            {"name": "\u793a\u4f8b\u5148\u8fdb\u5b9e\u9a8c\u5ba4", "aliases": ["\u793a\u4f8b\u5148\u8fdb\u5b9e\u9a8c\u5ba4", "\u5148\u8fdb\u6280\u672f\u4e2d\u5fc3"], "weight": 28},
        ],
    }
    return data


def make_notice(**changes):
    values = {
        "title": "\u5929\u7ebf\u6d4b\u91cf\u7cfb\u7edf\u91c7\u8d2d", "url": "x", "source": "test",
        "published_at": "2026-07-12T00:00:00+08:00", "deadline_at": "2026-08-10T00:00:00+08:00",
        "stage": "\u62db\u6807\u516c\u544a", "buyer": "\u67d0\u7814\u7a76\u9662", "region": "",
        "budget_cny": 2_000_000, "content": "\u91c7\u8d2d\u5929\u7ebf\u6d4b\u91cf\u7cfb\u7edf",
    }
    values.update(changes)
    return Notice(**values)


def test_southwest_notice_gets_region_boost():
    matcher = Matcher(sales_profile())
    southwest = matcher.score(make_notice(region="\u56db\u5ddd\u6210\u90fd"))
    outside = matcher.score(make_notice(region="\u5e7f\u4e1c\u6df1\u5733"))
    assert southwest.score == outside.score + 10
    assert southwest.region_match is True
    assert outside.region_match is False


def test_priority_account_alias_gets_major_boost():
    matcher = Matcher(sales_profile())
    priority = matcher.score(make_notice(buyer="\u793a\u4f8b\u7814\u7a76\u9662", region="\u56db\u5ddd"))
    ordinary = matcher.score(make_notice(buyer="\u67d0\u7814\u7a76\u9662", region="\u56db\u5ddd"))
    assert priority.score >= ordinary.score + 20
    assert priority.priority_account_hits == ["\u793a\u4f8b\u7814\u7a76\u9662"]


def test_below_budget_threshold_is_penalized_and_warned():
    result = Matcher(sales_profile()).score(make_notice(budget_cny=900_000))
    assert result.budget_status == "\u4f4e\u4e8e100\u4e07\u5143\u8ddf\u8fdb\u95e8\u69db"
    assert any("\u4f4e\u4e8e100\u4e07\u5143" in risk for risk in result.risks)


def test_unknown_budget_is_not_excluded():
    result = Matcher(sales_profile()).score(make_notice(budget_cny=None))
    assert result.score >= 30
    assert result.budget_status.startswith("\u9884\u7b97\u672a\u77e5")
    assert any("\u4e0d\u80fd\u6309\u91d1\u989d\u95e8\u69db\u76f4\u63a5\u6392\u9664" in risk for risk in result.risks)


def test_exact_budget_threshold_qualifies():
    result = Matcher(sales_profile()).score(make_notice(budget_cny=1_000_000))
    assert result.budget_status == "\u8fbe\u5230100\u4e07\u5143\u8ddf\u8fdb\u95e8\u69db"
    assert any("\u8fbe\u5230100\u4e07\u5143" in reason for reason in result.reasons)


def test_783_alias_matches_priority_account():
    result = Matcher(sales_profile()).score(make_notice(buyer="\u7ef5\u9633\u793a\u4f8b\u5b9e\u9a8c\u5ba4", region="\u56db\u5ddd"))
    assert result.priority_account_hits == ["\u793a\u4f8b\u5b9e\u9a8c\u5ba4"]


def test_score_contributions_reconcile_and_include_time_signals():
    notice = make_notice(
        published_at="2026-07-12T00:00:00+08:00",
        deadline_at="2026-07-20T00:00:00+08:00",
        stage="\u62db\u6807\u516c\u544a",
        region="\u56db\u5ddd",
    )
    result = Matcher(sales_profile()).score(
        notice, now=datetime.fromisoformat("2026-07-13T00:00:00+08:00")
    )
    assert sum(item["points"] for item in result.contributions) == result.score
    categories = {item["category"] for item in result.contributions}
    assert {"business_line", "stage", "region", "budget", "recency", "deadline"} <= categories
    assert next(item for item in result.contributions if item["category"] == "recency")["points"] == 5


def test_old_publication_receives_recency_penalty():
    result = Matcher(profile()).score(
        make_notice(published_at="2025-01-01", deadline_at=None),
        now=datetime.fromisoformat("2026-07-13T00:00:00+08:00"),
    )
    recency = next(item for item in result.contributions if item["category"] == "recency")
    assert recency["points"] == -5
    assert sum(item["points"] for item in result.contributions) == result.score
