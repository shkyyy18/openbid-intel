import csv

from bid_intel.exports import CRM_FIELDS, write_crm_csv


def test_crm_export_is_excel_friendly_and_quotes_non_ascii(tmp_path):
    target = write_crm_csv(tmp_path / "opportunities.csv", [{
        "id": 42,
        "title": 'Campus "AI", platform',
        "buyer": "\u67d0\u5927\u5b66",
        "region": "??",
        "budget_cny": 1200000,
        "stage": "request for proposal",
        "score": 88,
        "published_at": "2026-07-12",
        "deadline_at": None,
        "url": "https://example.invalid/42",
        "latest_verdict": "??",
        "content": "must not be exported",
        "raw_json": "must not be exported",
        "internal_note": "must not be exported",
        "result": {"business_lines": ["Data, AI and cloud", "Cybersecurity"]},
    }])
    payload = target.read_bytes()
    assert payload.startswith(b"\xef\xbb\xbf")
    with target.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert tuple(rows[0]) == CRM_FIELDS
    assert rows[0]["notice_id"] == "42"
    assert rows[0]["title"] == 'Campus "AI", platform'
    assert rows[0]["buyer"] == "\u67d0\u5927\u5b66"
    assert rows[0]["business_lines"] == "Data, AI and cloud; Cybersecurity"
    assert rows[0]["deadline_at"] == ""
    assert "content" not in rows[0]
    assert "internal_note" not in rows[0]


def test_crm_export_writes_header_for_empty_result(tmp_path):
    target = write_crm_csv(tmp_path / "empty.csv", [])
    with target.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    assert rows == [list(CRM_FIELDS)]
