"""Tests for pipeline/domains/engine/extract_enums.py"""
import json
import pytest
from pathlib import Path
from pipeline.domains.engine.extract_enums import extract_enum_from_file, run_enums


FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


def make_enum_file(tmp_path, name, names_dict, display_map=None):
    """Helper: write a UserDefinedEnum JSON file."""
    display_map = display_map or []
    data = [{
        "Type": "UserDefinedEnum",
        "Name": name,
        "Names": names_dict,
        "Properties": {"DisplayNameMap": display_map}
    }]
    f = tmp_path / f"{name}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_enum_returns_name_and_values(tmp_path):
    f = make_enum_file(tmp_path, "E_Foo", {"E_Foo::Val0": 0, "E_Foo::Val1": 1, "E_Foo::_MAX": 2})
    result = extract_enum_from_file(f)
    assert result["name"] == "E_Foo"
    assert len(result["values"]) == 2  # _MAX excluded


def test_extract_enum_uses_display_names(tmp_path):
    display_map = [
        {"Key": "Val0", "Value": {"CultureInvariantString": "Zero"}},
        {"Key": "Val1", "Value": {"CultureInvariantString": "One"}},
    ]
    f = make_enum_file(tmp_path, "E_Bar",
                       {"E_Bar::Val0": 0, "E_Bar::Val1": 1, "E_Bar::_MAX": 2},
                       display_map)
    result = extract_enum_from_file(f)
    by_index = {v["index"]: v["displayName"] for v in result["values"]}
    assert by_index[0] == "Zero"
    assert by_index[1] == "One"


def test_extract_enum_sorts_by_index(tmp_path):
    f = make_enum_file(tmp_path, "E_Baz", {"E_Baz::C": 2, "E_Baz::A": 0, "E_Baz::B": 1})
    result = extract_enum_from_file(f)
    indices = [v["index"] for v in result["values"]]
    assert indices == sorted(indices)


def test_extract_enum_returns_none_for_non_enum(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "Other", "Name": "Foo"}]', encoding="utf-8")
    assert extract_enum_from_file(f) is None


def test_run_enums_writes_output(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    make_enum_file(raw_dir, "E_Test", {"E_Test::A": 0, "E_Test::_MAX": 1})
    extracted_dir = tmp_path / "extracted"
    result = run_enums(raw_dir=raw_dir, extracted_root=extracted_dir)
    assert "E_Test" in result  # return value check per spec
    out = extracted_dir / "engine" / "enums.json"
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "E_Test" in data
