import json

from bid_intel.importers import canonicalize_record, load_notices


def test_common_export_field_aliases_are_detected(tmp_path):
    path = tmp_path / "export.json"
    path.write_text(json.dumps({"items": [{
        "Project Name": "Cloud data platform RFP",
        "Notice Link": "https://example.invalid/1",
        "Published Date": "2026-07-12",
        "Purchasing Organization": "Example Agency",
        "Estimated Value": "$1.25 million",
        "Description": "Data governance and private cloud",
    }]}), encoding="utf-8")
    mapping = tmp_path / "mapping.json"
    mapping.write_text(json.dumps({
        "title": "Project Name", "url": "Notice Link", "published_at": "Published Date",
        "buyer": "Purchasing Organization", "budget_cny": "Estimated Value", "content": "Description",
    }), encoding="utf-8")
    notice = load_notices(path, mapping)[0]
    assert notice.title == "Cloud data platform RFP"
    assert notice.budget_cny == 1_250_000
    assert notice.source == "export"


def test_amount_parser_handles_chinese_ten_thousand_unit():
    row = canonicalize_record({"title": "x", "published_at": "2026-07-12", "budget": "125\u4e07\u5143"})
    assert row["budget_cny"] == 1_250_000
