import json

import pytest

from io import StringIO

from bid_intel.onboarding import choose_profile
from bid_intel.profiles import list_profiles, load_builtin_profile, write_profile


def test_builtin_profiles_cover_popular_sectors():
    ids = {row["id"] for row in list_profiles()}
    assert {"it-digital", "construction", "medical-lab", "marketing-services", "energy-sustainability", "education"} <= ids


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


def test_every_builtin_profile_validates_against_schema(tmp_path):
    from bid_intel.config_validation import validate_config

    for row in list_profiles():
        target = write_profile(row["id"], tmp_path / f"{row['id']}.json")
        assert validate_config(target, "profile") == [], row["id"]
        assert "?" * 3 not in target.read_text(encoding="utf-8")


def test_interactive_profile_selection_accepts_number_and_default():
    output = StringIO()
    assert choose_profile(StringIO("\n"), output) == "it-digital"
    profiles = list_profiles()
    education_number = next(index for index, row in enumerate(profiles, start=1) if row["id"] == "education")
    assert choose_profile(StringIO(f"{education_number}\n"), StringIO()) == "education"
    assert "Choose an industry profile" in output.getvalue()
