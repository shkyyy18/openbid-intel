import json
from io import StringIO

import pytest

from bid_intel.matcher import Matcher
from bid_intel.models import Notice
from bid_intel.onboarding import choose_profile
from bid_intel.profiles import list_profiles, load_builtin_profile, write_profile


def test_builtin_profiles_cover_popular_sectors():
    ids = {row["id"] for row in list_profiles()}
    assert {
        "it-digital", "construction", "medical-lab", "marketing-services",
        "energy-sustainability", "education", "logistics", "facilities-management",
    } <= ids


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


def test_logistics_profile_is_broad_specific_and_neutral():
    profile = load_builtin_profile("logistics")
    lines = profile["business_lines"]
    assert {line["id"] for line in lines} == {
        "transportation_distribution",
        "warehousing_fulfillment",
        "cold_chain_fleet_equipment",
    }
    assert profile["focus_regions"] == []
    assert profile["min_budget_cny"] == 0
    assert profile["sales_profile"]["priority_accounts"] == []
    assert profile["sales_profile"]["focus_regions"] == []
    terms = {
        term.lower()
        for line in lines
        for key in ("strong_terms", "related_terms")
        for term in line[key]
    }
    assert not ({"service", "vehicle", "transport", "warehouse", "logistics"} & terms)


@pytest.mark.parametrize(
    ("title", "expected_line"),
    [
        ("Regional line-haul transportation tender", "Transportation and distribution"),
        ("Warehouse management system and order fulfillment services", "Warehousing, fulfillment, and supply-chain services"),
        ("Cold chain logistics and fleet management system", "Cold chain, fleet technology, and logistics equipment"),
    ],
)
def test_logistics_profile_matches_distinct_opportunity_types(title, expected_line):
    notice = Notice(
        title=title, url="https://example.invalid/tender", source="fixture",
        published_at="2026-07-13", stage="tender notice", buyer="Example organization",
    )
    result = Matcher(load_builtin_profile("logistics")).score(notice)
    assert expected_line in result.business_lines
    assert result.score >= 30


def test_facilities_profile_is_broad_specific_and_neutral():
    profile = load_builtin_profile("facilities-management")
    lines = profile["business_lines"]
    assert {line["id"] for line in lines} == {
        "property_facility_management",
        "cleaning_landscaping_waste",
        "building_technical_services",
    }
    assert profile["focus_regions"] == []
    assert profile["min_budget_cny"] == 0
    assert profile["sales_profile"]["priority_accounts"] == []
    assert profile["sales_profile"]["focus_regions"] == []
    terms = {
        term.lower()
        for line in lines
        for key in ("strong_terms", "related_terms")
        for term in line[key]
    }
    assert not ({"service", "maintenance", "property", "cleaning", "building", "facilities"} & terms)


@pytest.mark.parametrize(
    ("title", "expected_line"),
    [
        ("Integrated facilities management tender", "Property and facility management services"),
        ("Commercial cleaning and landscaping maintenance services", "Cleaning, landscaping, pest control, and waste services"),
        ("HVAC and elevator maintenance contract", "Building maintenance and technical services"),
    ],
)
def test_facilities_profile_matches_distinct_opportunity_types(title, expected_line):
    notice = Notice(
        title=title, url="https://example.invalid/tender", source="fixture",
        published_at="2026-07-13", stage="tender notice", buyer="Example organization",
    )
    result = Matcher(load_builtin_profile("facilities-management")).score(notice)
    assert expected_line in result.business_lines
    assert result.score >= 30
