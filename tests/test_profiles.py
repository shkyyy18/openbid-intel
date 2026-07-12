import json

import pytest

from bid_intel.profiles import list_profiles, load_builtin_profile, write_profile


def test_builtin_profiles_cover_popular_sectors():
    ids = {row["id"] for row in list_profiles()}
    assert {"it-digital", "construction", "medical-lab", "marketing-services", "energy-sustainability"} <= ids


def test_write_profile_creates_editable_json(tmp_path):
    target = write_profile("medical-lab", tmp_path / "profile.json")
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["meta"]["id"] == "medical-lab"
    assert len(data["business_lines"]) >= 2
    with pytest.raises(FileExistsError):
        write_profile("it-digital", target)


def test_unknown_profile_lists_choices():
    with pytest.raises(ValueError, match="it-digital"):
        load_builtin_profile("does-not-exist")
