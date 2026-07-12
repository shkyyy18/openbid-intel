from datetime import datetime, timezone

from bid_intel.dashboard import render_dashboard, write_dashboard


def sample_row(**changes):
    row = {
        "id": 1,
        "title": "City data platform RFP",
        "url": "https://example.invalid/tender/1",
        "source": "Open data portal",
        "published_at": "2026-07-12",
        "deadline_at": "2026-08-01",
        "stage": "request for proposal",
        "buyer": "Example City",
        "region": "Example Region",
        "budget_cny": 4_200_000,
        "score": 91,
        "level": "Priority",
        "result": {
            "business_lines": ["Data, AI and cloud"],
            "reasons": ["Matched data platform", "Budget is qualified"],
            "recommended_actions": ["Verify requirements", "Assign an owner"],
        },
    }
    row.update(changes)
    return row


def test_dashboard_is_self_contained_and_filterable(tmp_path):
    target = write_dashboard(tmp_path / "dashboard.html", [sample_row()])
    text = target.read_text(encoding="utf-8")
    assert "<!doctype html>" in text
    assert "City data platform RFP" in text
    assert 'id="search"' in text
    assert 'id="stage"' in text
    assert "card.dataset.search.includes" in text
    assert "https://example.invalid/tender/1" in text
    assert "<script>" in text and "<style>" in text


def test_dashboard_escapes_content_and_rejects_unsafe_urls():
    row = sample_row(title='<script>alert("x")</script>', url="javascript:alert(1)")
    text = render_dashboard([row], generated_at=datetime(2026, 7, 12, tzinfo=timezone.utc))
    assert '<script>alert("x")</script>' not in text
    assert "&lt;script&gt;alert" in text
    assert 'href="#"' in text
    assert "javascript:alert(1)" not in text


def test_empty_dashboard_has_clear_state():
    text = render_dashboard([])
    assert "No opportunities match the current filters." in text
    assert 'class="empty visible"' in text
    assert 'id="visibleStat">0<' in text
