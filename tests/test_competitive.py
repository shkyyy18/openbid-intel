from bid_intel.competitive import analyze_awards, build_relationships, infer_supplier_role, render_competitor_report, resolve_buyer_aliases, summarize_suppliers


def profile():
    return {"business_lines": [
        {"id": "measurement", "name": "\u7535\u78c1\u573a\u6d4b\u91cf", "strong_terms": ["\u5929\u7ebf\u8fd1\u573a\u6d4b\u91cf"], "related_terms": ["\u5fae\u6ce2\u6697\u5ba4", "\u8f6c\u53f0"]},
        {"id": "cae", "name": "CAE\u7535\u78c1\u4eff\u771f", "strong_terms": ["\u7535\u78c1\u4eff\u771f\u8f6f\u4ef6"], "related_terms": ["\u5e76\u884c\u8ba1\u7b97"]},
    ]}


def history():
    return [
        {"title": "\u5929\u7ebf\u8fd1\u573a\u6d4b\u91cf\u7cfb\u7edf\u4e2d\u6807", "content": "\u5fae\u6ce2\u6697\u5ba4\u4e0e\u8f6c\u53f0", "buyer": "\u793a\u4f8b\u6280\u672f\u5927\u5b66", "region": "\u56db\u5ddd", "published_at": "2026-01-01", "award_supplier": "\u6210\u90fd\u67d0\u6d4b\u63a7\u79d1\u6280\u80a1\u4efd\u516c\u53f8", "award_amount_cny": 3_000_000, "url": "u1"},
        {"title": "\u7269\u4e1a\u670d\u52a1\u4e2d\u6807", "content": "\u4fdd\u6d01\u670d\u52a1", "buyer": "\u793a\u4f8b\u6280\u672f\u5927\u5b66", "region": "\u56db\u5ddd", "published_at": "2026-01-02", "award_supplier": "\u67d0\u7269\u4e1a\u670d\u52a1\u516c\u53f8", "award_amount_cny": 1_000_000, "url": "u2"},
    ]


def test_analyze_awards_filters_unrelated_and_classifies_line():
    rows = analyze_awards(history(), profile())
    assert len(rows) == 1
    assert rows[0]["business_lines"] == ["\u7535\u78c1\u573a\u6d4b\u91cf"]
    assert rows[0]["relevance"] == "\u9ad8\u76f8\u5173"


def test_supplier_summary_and_relationships():
    rows = analyze_awards(history(), profile())
    summary = summarize_suppliers(rows)
    assert summary[0]["award_count"] == 1
    assert summary[0]["total_award_cny"] == 3_000_000
    relations = build_relationships(rows)
    assert relations[0]["buyer"] == "\u793a\u4f8b\u6280\u672f\u5927\u5b66"
    assert relations[0]["business_line"] == "\u7535\u78c1\u573a\u6d4b\u91cf"


def test_product_line_filter_accepts_id():
    rows = analyze_awards(history(), profile(), product_line="measurement")
    assert len(rows) == 1
    assert analyze_awards(history(), profile(), product_line="cae") == []


def test_resolve_buyer_aliases():
    p = {"sales_profile": {"priority_accounts": [{"name": "\u793a\u4f8b\u7814\u7a76\u9662", "aliases": ["\u793a\u4f8b\u7814\u7a76\u9662"]}]}}
    label, aliases = resolve_buyer_aliases(p, "\u793a\u4f8b\u7814\u7a76\u9662")
    assert label == "\u793a\u4f8b\u7814\u7a76\u9662"
    assert "\u793a\u4f8b\u7814\u7a76\u9662" in aliases


def test_supplier_role_heuristics_cover_channel_and_manufacturer():
    line_matches = [{"name": "\u7535\u78c1\u573a\u6d4b\u91cf"}]
    channel, _ = infer_supplier_role("\u6210\u90fd\u67d0\u7cfb\u7edf\u5de5\u7a0b\u79d1\u6280\u516c\u53f8", "", line_matches)
    maker, _ = infer_supplier_role("\u67d0\u5fae\u6ce2\u4eea\u5668\u5236\u9020\u516c\u53f8", "", line_matches)
    service, _ = infer_supplier_role("\u67d0\u68c0\u6d4b\u670d\u52a1\u516c\u53f8", "", line_matches)
    assert channel == "\u7591\u4f3c\u96c6\u6210/\u7ecf\u9500\u670d\u52a1\u5546"
    assert maker == "\u7591\u4f3c\u8bbe\u5907/\u8f6f\u4ef6\u5382\u5546"
    assert service == "\u7591\u4f3c\u670d\u52a1\u5546"


def test_report_unknown_amount_and_disclaimer():
    rows = analyze_awards([{
        "title": "\u5929\u7ebf\u8fd1\u573a\u6d4b\u91cf\u7cfb\u7edf\u4e2d\u6807", "content": "", "buyer": "\u67d0\u9662",
        "published_at": "2026-01-01", "award_supplier": "\u67d0\u79d1\u6280\u516c\u53f8", "award_amount_cny": None, "url": "u"
    }], profile())
    report = render_competitor_report(summarize_suppliers(rows), rows, relationships=build_relationships(rows))
    assert "\u5f85\u786e\u8ba4" in report
    assert "\u542f\u53d1\u5f0f\u521d\u5224" in report
    assert "\u4e0d\u5fc5\u7136\u662f\u970d\u83b1\u6c83\u7684\u76f4\u63a5\u7ade\u4e89\u5bf9\u624b" in report
