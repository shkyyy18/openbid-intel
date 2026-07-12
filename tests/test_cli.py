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
    assert sum(name.startswith("account_") for name in names) == 2
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
