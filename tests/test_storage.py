from bid_intel.models import Notice, ScoreResult
from bid_intel.storage import Store


def test_store_deduplicates_by_url(tmp_path):
    store = Store(tmp_path / "bids.db")
    first = Notice(title="项目A", url="https://example.com/a?utm_source=x", source="x", published_at="2026-01-01")
    second = Notice(title="项目A更新", url="https://example.com/a", source="x", published_at="2026-01-02")
    first_id, created_first = store.upsert_notice(first)
    second_id, created_second = store.upsert_notice(second)
    assert created_first is True
    assert created_second is False
    assert first_id == second_id
    assert store.stats()["notices"] == 1


def test_rank_and_feedback(tmp_path):
    store = Store(tmp_path / "bids.db")
    notice_id, _ = store.upsert_notice(Notice(title="项目", url="u", source="s", published_at="2026-01-01"))
    score = ScoreResult(88, "重点", ["仿真"], ["电磁仿真"], [], [], [], ["核心匹配"], [], ["跟进"])
    store.save_score(notice_id, score)
    store.add_feedback(notice_id, "已跟进", "联系代理")
    rows = store.ranked()
    assert rows[0]["score"] == 88
    assert rows[0]["latest_verdict"] == "已跟进"


def test_data_quality_counts_only_fetched_details(tmp_path):
    store = Store(tmp_path / "quality.db")
    listed = Notice(title="\u5217\u8868\u516c\u544a", url="1", source="s", published_at="2026-01-01", content="\u5217\u8868\u516c\u544a")
    detailed = Notice(title="\u8be6\u60c5\u516c\u544a", url="2", source="s", published_at="2026-01-01", content="\u5b8c\u6574\u6b63\u6587", raw={"detail_fetched_at": "2026-01-01T00:00:00+08:00"})
    store.upsert_notice(listed); store.upsert_notice(detailed)
    assert store.data_quality()["with_details"] == 1


def test_source_quality_reports_per_source_success_rate(tmp_path):
    store = Store(tmp_path / "runs.db")
    store.add_collection_run("a", "\u6765\u6e90A", "ok", 20, 20, 0, "", "s", "f")
    store.add_collection_run("a", "\u6765\u6e90A", "error", 0, 0, 0, "x", "s", "f")
    row = store.source_quality()[0]
    assert row["runs"] == 2
    assert row["success_rate"] == 50.0


def test_award_history_matches_any_buyer_alias(tmp_path):
    store = Store(tmp_path / "aliases.db")
    store.upsert_notice(Notice(title="a", url="1", source="s", published_at="2026-01-01", buyer="\u4e2d\u7535\u79d1\u4e8c\u5341\u4e5d\u6240", award_supplier="\u67d0\u516c\u53f8"))
    store.upsert_notice(Notice(title="b", url="2", source="s", published_at="2026-01-01", buyer="\u7535\u5b50\u79d1\u6280\u5927\u5b66", award_supplier="\u53e6\u4e00\u516c\u53f8"))
    rows = store.award_history(buyer_queries=["\u6210\u90fd29\u6240", "\u4e8c\u5341\u4e5d\u6240"], limit=100)
    assert len(rows) == 1
    assert rows[0]["buyer"] == "\u4e2d\u7535\u79d1\u4e8c\u5341\u4e5d\u6240"


def test_updating_notice_invalidates_stale_score(tmp_path):
    store = Store(tmp_path / "rescore.db")
    notice = Notice(title="\u9879\u76ee", url="u", source="s", published_at="2026-01-01", content="\u5217\u8868")
    notice_id, _ = store.upsert_notice(notice)
    store.save_score(notice_id, ScoreResult(10, "\u666e\u901a", [], [], [], [], [], [], [], []))
    notice.content = "\u5929\u7ebf\u8fd1\u573a\u6d4b\u91cf\u7cfb\u7edf\u8be6\u60c5"
    store.upsert_notice(notice)
    assert [item[0] for item in store.unscored_notices()] == [notice_id]
