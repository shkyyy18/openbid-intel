import json
from pathlib import Path

from bid_intel.cli import main


def test_intelligence_workflow_generates_complete_report_bundle(tmp_path):
    sources = tmp_path / "sources.json"
    sources.write_text(json.dumps({"sources": []}), encoding="utf-8")
    output = tmp_path / "reports"
    rc = main([
        "--db", str(tmp_path / "bids.db"),
        "--sources", str(sources),
        "intelligence", "--output-dir", str(output), "--no-push", "--no-details",
    ])
    assert rc == 0
    names = {path.name for path in output.glob("*.md")}
    assert any(name.startswith("digest_") for name in names)
    assert any(name.startswith("competitors_") for name in names)
    assert any(name.startswith("quality_") for name in names)
    root = Path(__file__).resolve().parents[1]
    profile = json.loads((root / "config" / "profile.json").read_text(encoding="utf-8"))
    expected_accounts = len(profile.get("sales_profile", {}).get("priority_accounts", []))
    assert sum(name.startswith("account_") for name in names) == expected_accounts
    quality = next(output.glob("quality_*.md")).read_text(encoding="utf-8")
    assert "\u6570\u636e\u8d28\u91cf\u62a5\u544a" in quality
    assert "\u5404\u6765\u6e90\u5386\u53f2\u6210\u529f\u7387" in quality


def test_release_check_passes_for_repository(tmp_path):
    root = Path(__file__).resolve().parents[1]
    rc = main([
        "--db", str(tmp_path / "release.db"),
        "release-check", "--root", str(root),
    ])
    assert rc == 0


def test_profile_commands_and_mapping_argument(tmp_path, capsys):
    assert main(["profiles"]) == 0
    output = capsys.readouterr().out
    assert "it-digital" in output
    target = tmp_path / "profile.json"
    assert main(["init-profile", "construction", "--output", str(target)]) == 0
    assert json.loads(target.read_text(encoding="utf-8"))["meta"]["id"] == "construction"

    source = tmp_path / "notices.csv"
    source.write_text("Project Name,Notice Link,Published Date\nExample cloud RFP,https://example.invalid/1,2026-07-12\n", encoding="utf-8")
    mapping = tmp_path / "mapping.json"
    mapping.write_text(json.dumps({"title": "Project Name", "url": "Notice Link", "published_at": "Published Date"}), encoding="utf-8")
    assert main(["--db", str(tmp_path / "mapped.db"), "import", str(source), "--mapping", str(mapping)]) == 0


def test_demo_and_dashboard_commands_generate_html(tmp_path):
    root = Path(__file__).resolve().parents[1]
    database = tmp_path / "demo.db"
    digest = tmp_path / "demo.md"
    dashboard = tmp_path / "demo.html"
    rc = main([
        "--db", str(database),
        "--profile", str(root / "config" / "profile.json"),
        "demo",
        "--sample", str(root / "samples" / "demo_notices.json"),
        "--output", str(digest),
        "--dashboard-output", str(dashboard),
    ])
    assert rc == 0
    assert digest.is_file()
    assert "Opportunity Dashboard" in dashboard.read_text(encoding="utf-8")

    filtered = tmp_path / "filtered.html"
    assert main(["--db", str(database), "dashboard", "--min-score", "50", "--output", str(filtered)]) == 0
    assert filtered.is_file()
    assert 'id="search"' in filtered.read_text(encoding="utf-8")


def test_validate_config_command(tmp_path, capsys):
    root = Path(__file__).resolve().parents[1]
    assert main([
        "--profile", str(root / "config/profile.json"),
        "--sources", str(root / "config/sources.json"),
        "validate-config",
    ]) == 0
    assert "[OK] profile" in capsys.readouterr().out

    invalid = tmp_path / "invalid.json"
    invalid.write_text('{"business_lines":[]}', encoding="utf-8")
    assert main(["--profile", str(invalid), "validate-config", "--only", "profile"]) == 1
    assert "array must contain at least 1 item" in capsys.readouterr().out


def test_export_command_generates_crm_csv(tmp_path):
    root = Path(__file__).resolve().parents[1]
    database = tmp_path / "export.db"
    assert main([
        "--db", str(database),
        "--profile", str(root / "config/profile.json"),
        "demo",
        "--sample", str(root / "samples/demo_notices.json"),
        "--output", str(tmp_path / "demo.md"),
        "--dashboard-output", str(tmp_path / "demo.html"),
    ]) == 0
    target = tmp_path / "qualified.csv"
    assert main(["--db", str(database), "export", "--min-score", "50", "--output", str(target)]) == 0
    text = target.read_text(encoding="utf-8-sig")
    assert "notice_id,title,buyer,region,budget_cny" in text
    assert "City data platform and AI knowledge assistant RFP" in text
