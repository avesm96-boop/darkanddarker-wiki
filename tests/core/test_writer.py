"""Tests for pipeline/core/writer.py"""
import json
import pytest
from pathlib import Path
from pipeline.core.writer import Writer

PIPELINE_VERSION = "1.0.0"


@pytest.fixture
def writer(tmp_path):
    return Writer(extracted_root=tmp_path, pipeline_version=PIPELINE_VERSION)


def test_write_entity_creates_file(writer, tmp_path):
    writer.write_entity("items", "sword", {"id": "sword", "name": "Sword"}, source_files=["raw/x.json"])
    out = tmp_path / "items" / "sword.json"
    assert out.exists()


def test_write_entity_adds_meta(writer, tmp_path):
    writer.write_entity("items", "sword", {"id": "sword"}, source_files=["raw/x.json"])
    data = json.loads((tmp_path / "items" / "sword.json").read_text(encoding="utf-8"))
    assert "_meta" in data
    assert data["_meta"]["pipeline_version"] == PIPELINE_VERSION
    assert isinstance(data["_meta"]["source_files"], list)
    assert "raw/x.json" in data["_meta"]["source_files"]
    assert "extracted_at" in data["_meta"]


def test_write_entity_meta_is_last_key(writer, tmp_path):
    writer.write_entity("items", "sword", {"id": "sword", "name": "X"}, source_files=[])
    data = json.loads((tmp_path / "items" / "sword.json").read_text(encoding="utf-8"))
    assert list(data.keys())[-1] == "_meta"


def test_write_index_creates_index_file(writer, tmp_path):
    entries = [{"id": "sword", "name": "Sword"}]
    writer.write_index("items", entries)
    out = tmp_path / "items" / "_index.json"
    assert out.exists()


def test_write_index_structure(writer, tmp_path):
    entries = [{"id": "a"}, {"id": "b"}]
    writer.write_index("items", entries)
    data = json.loads((tmp_path / "items" / "_index.json").read_text(encoding="utf-8"))
    assert data["count"] == 2
    assert data["entries"] == entries
    assert "_meta" in data


def test_write_system_creates_file(writer, tmp_path):
    writer.write_system("engine", "curves", {"data": 123}, source_files=["raw/ct.json"])
    out = tmp_path / "engine" / "curves.json"
    assert out.exists()


def test_write_system_adds_meta(writer, tmp_path):
    writer.write_system("engine", "curves", {"data": 123}, source_files=["raw/a.json", "raw/b.json"])
    data = json.loads((tmp_path / "engine" / "curves.json").read_text(encoding="utf-8"))
    assert data["_meta"]["source_files"] == ["raw/a.json", "raw/b.json"]


def test_creates_domain_directory_if_missing(writer, tmp_path):
    writer.write_entity("newdomain", "thing", {"id": "thing"}, source_files=[])
    assert (tmp_path / "newdomain").is_dir()
