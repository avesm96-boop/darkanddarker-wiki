"""Tests for pipeline/core/reader.py"""
import json
import pytest
from pathlib import Path
from pipeline.core.reader import load, find_files, find_by_type, get_properties, get_item

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_load_returns_list(tmp_path):
    f = tmp_path / "test.json"
    f.write_text('[{"Type": "Foo", "Name": "Bar"}]', encoding="utf-8")
    result = load(f)
    assert isinstance(result, list)
    assert result[0]["Type"] == "Foo"


def test_load_wraps_bare_object_in_list(tmp_path):
    """load() must return list[dict] even when JSON root is a bare object."""
    f = tmp_path / "bare.json"
    f.write_text('{"Type": "Foo"}', encoding="utf-8")
    result = load(f)
    assert isinstance(result, list)
    assert result[0]["Type"] == "Foo"


def test_load_raises_on_missing_file():
    with pytest.raises(FileNotFoundError):
        load(Path("/nonexistent/path/file.json"))


def test_load_raises_on_invalid_json(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("not json", encoding="utf-8")
    with pytest.raises(ValueError):
        load(f)


def test_find_files_finds_matching_files(tmp_path):
    (tmp_path / "a.json").write_text("[]", encoding="utf-8")
    (tmp_path / "b.json").write_text("[]", encoding="utf-8")
    (tmp_path / "c.txt").write_text("", encoding="utf-8")
    results = find_files(str(tmp_path / "*.json"))
    assert len(results) == 2
    assert all(p.suffix == ".json" for p in results)


def test_find_files_returns_sorted_paths(tmp_path):
    for name in ["c.json", "a.json", "b.json"]:
        (tmp_path / name).write_text("[]", encoding="utf-8")
    results = find_files(str(tmp_path / "*.json"))
    names = [p.name for p in results]
    assert names == sorted(names)


def test_find_files_returns_empty_list_for_no_matches(tmp_path):
    results = find_files(str(tmp_path / "*.json"))
    assert results == []


def test_find_by_type_returns_matching_files(tmp_path):
    f1 = tmp_path / "enum1.json"
    f1.write_text('[{"Type": "UserDefinedEnum", "Name": "E_Test"}]', encoding="utf-8")
    f2 = tmp_path / "other.json"
    f2.write_text('[{"Type": "Other", "Name": "X"}]', encoding="utf-8")
    results = find_by_type("UserDefinedEnum", tmp_path)
    assert len(results) == 1
    assert results[0].name == "enum1.json"


def test_find_by_type_recurses_into_subdirectories(tmp_path):
    sub = tmp_path / "subdir"
    sub.mkdir()
    (sub / "nested.json").write_text('[{"Type": "UserDefinedEnum", "Name": "E_Nested"}]', encoding="utf-8")
    results = find_by_type("UserDefinedEnum", tmp_path)
    assert any(p.name == "nested.json" for p in results)


def test_get_properties_extracts_properties():
    obj = {"Type": "Foo", "Properties": {"A": 1, "B": 2}}
    assert get_properties(obj) == {"A": 1, "B": 2}


def test_get_properties_returns_empty_dict_on_missing():
    obj = {"Type": "Foo"}
    assert get_properties(obj) == {}


def test_get_properties_returns_empty_dict_on_null():
    assert get_properties({"Properties": None}) == {}


def test_get_item_extracts_item_struct():
    obj = {"Properties": {"Item": {"MaxStack": 5}}}
    assert get_item(obj) == {"MaxStack": 5}


def test_get_item_returns_empty_dict_on_missing():
    obj = {"Properties": {}}
    assert get_item(obj) == {}
