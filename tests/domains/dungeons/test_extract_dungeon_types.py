"""Tests for pipeline/domains/dungeons/extract_dungeon_types.py"""
import json
from pathlib import Path
from pipeline.domains.dungeons.extract_dungeon_types import extract_dungeon_type, run_dungeon_types


def make_dungeon_type_file(tmp_path, type_id):
    data = [{
        "Type": "DCDungeonTypeDataAsset",
        "Name": type_id,
        "Properties": {
            "IdTag": {"TagName": "DungeonType.Crypts"},
            "Name": {"LocalizedString": "Crypts"},
            "GroupName": {"LocalizedString": "Underground"},
            "ChapterName": {"LocalizedString": "Chapter 1"},
            "Desc": {"LocalizedString": "Dark underground dungeons"},
            "Order": 1,
        }
    }]
    f = tmp_path / f"{type_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_dungeon_type_returns_id_and_fields(tmp_path):
    f = make_dungeon_type_file(tmp_path, "Id_DungeonType_Crypts")
    result = extract_dungeon_type(f)
    assert result is not None
    assert result["id"] == "Id_DungeonType_Crypts"
    assert result["id_tag"] == "DungeonType.Crypts"
    assert result["name"] == "Crypts"
    assert result["group_name"] == "Underground"
    assert result["chapter_name"] == "Chapter 1"
    assert result["desc"] == "Dark underground dungeons"
    assert result["order"] == 1


def test_extract_dungeon_type_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_dungeon_type(f) is None


def test_run_dungeon_types_writes_entity_and_index(tmp_path):
    type_dir = tmp_path / "dungeon_type"
    type_dir.mkdir()
    make_dungeon_type_file(type_dir, "Id_DungeonType_Crypts")
    extracted = tmp_path / "extracted"
    result = run_dungeon_types(dungeon_type_dir=type_dir, extracted_root=extracted)
    entity = extracted / "dungeons" / "Id_DungeonType_Crypts.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id_tag"] == "DungeonType.Crypts"
    assert "_meta" in data
    index = extracted / "dungeons" / "_index.json"
    assert index.exists()
    assert "Id_DungeonType_Crypts" in result
