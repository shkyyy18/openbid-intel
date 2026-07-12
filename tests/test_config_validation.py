from pathlib import Path

from bid_intel.config_validation import load_schema, validate_config, validate_instance


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures"


def test_bundled_schemas_validate_public_configs():
    assert validate_config(ROOT / "config/profile.json", "profile") == []
    assert validate_config(ROOT / "config/sources.json", "sources") == []


def test_invalid_profile_reports_nested_paths():
    errors = validate_config(FIXTURES / "invalid_profile.json", "profile")
    assert any("$.business_lines[0].id" in error for error in errors)
    assert any("missing required property 'related_terms'" in error for error in errors)
    assert any("$.business_lines[0].strong_terms" in error and "expected array" in error for error in errors)


def test_invalid_sources_reports_empty_url():
    errors = validate_config(FIXTURES / "invalid_sources.json", "sources")
    assert any("$.sources[0].url" in error for error in errors)


def test_semantic_validation_rejects_duplicate_ids_after_schema_passes(tmp_path):
    path = tmp_path / "sources.json"
    path.write_text('{"sources":[{"id":"same","name":"A","type":"x","url":"u"},{"id":"same","name":"B","type":"x","url":"u"}]}', encoding="utf-8")
    assert validate_config(path, "sources") == ["$.sources: duplicate id 'same'"]


def test_validator_distinguishes_boolean_from_integer():
    errors = validate_instance(True, {"type": "integer"})
    assert errors == ["$: expected integer, got boolean"]


def test_schema_documents_use_json_schema_2020_12():
    for kind in ("profile", "sources"):
        schema = load_schema(kind)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["type"] == "object"
