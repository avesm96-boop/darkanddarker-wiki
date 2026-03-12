"""Tests for pipeline/domains/quests/extract_triumph_levels.py"""
import json
from pathlib import Path
from pipeline.domains.quests.extract_triumph_levels import extract_triumph_level, run_triumph_levels


def make_triumph_level_file(tmp_path, triumph_level_id):
    data = [{"Type": "DCTriumphLevelDataAsset", "Name": triumph_level_id}]
    f = tmp_path / f"{triumph_level_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_triumph_level_returns_id(tmp_path):
    f = make_triumph_level_file(tmp_path, "Id_TriumphLevel_0")
    result = extract_triumph_level(f)
    assert result is not None
    assert result["id"] == "Id_TriumphLevel_0"


def test_extract_triumph_level_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_triumph_level(f) is None


def test_run_triumph_levels_writes_entity_and_index(tmp_path):
    tl_dir = tmp_path / "triumph_levels"
    tl_dir.mkdir()
    make_triumph_level_file(tl_dir, "Id_TriumphLevel_0")
    make_triumph_level_file(tl_dir, "Id_TriumphLevel_1")
    extracted = tmp_path / "extracted"
    result = run_triumph_levels(triumph_level_dir=tl_dir, extracted_root=extracted)
    entity = extracted / "quests" / "Id_TriumphLevel_0.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id"] == "Id_TriumphLevel_0"
    assert "_meta" in data
    index = extracted / "quests" / "_index.json"
    assert index.exists()
    assert "Id_TriumphLevel_0" in result
    assert "Id_TriumphLevel_1" in result
