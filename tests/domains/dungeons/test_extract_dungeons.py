"""Tests for pipeline/domains/dungeons/extract_dungeons.py"""
import json
from pathlib import Path
from pipeline.domains.dungeons.extract_dungeons import extract_dungeon, run_dungeons


def make_dungeon_file(tmp_path, dungeon_id):
    data = [{
        "Type": "DCDungeonDataAsset",
        "Name": dungeon_id,
        "Properties": {
            "IdTag": {"TagName": "Dungeon.Crypts"},
            "Name": {"LocalizedString": "Crypts"},
            "GameTypes": ["EGameType::Normal"],
            "DefaultDungeonGrade": 2,
            "floor": 1,
            "FloorRule": {"AssetPathName": "/Game/.../FR_Crypts.FR_Crypts", "SubPathString": ""},
            "TriumphExp": 100,
            "ModuleType": "EDCDungeonModuleType::Standard",
            "bFogEnabled": True,
            "NumMinEscapes": 3,
        }
    }]
    f = tmp_path / f"{dungeon_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_dungeon_returns_id_and_fields(tmp_path):
    f = make_dungeon_file(tmp_path, "Id_Dungeon_Crypts_A")
    result = extract_dungeon(f)
    assert result is not None
    assert result["id"] == "Id_Dungeon_Crypts_A"
    assert result["id_tag"] == "Dungeon.Crypts"
    assert result["name"] == "Crypts"
    assert result["game_types"] == ["EGameType::Normal"]
    assert result["default_dungeon_grade"] == 2
    assert result["floor"] == 1
    assert result["floor_rule"] == "FR_Crypts"
    assert result["triumph_exp"] == 100
    assert result["module_type"] == "EDCDungeonModuleType::Standard"
    assert result["fog_enabled"] is True
    assert result["num_min_escapes"] == 3


def test_extract_dungeon_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_dungeon(f) is None


def test_run_dungeons_writes_entity_and_index(tmp_path):
    dungeon_dir = tmp_path / "dungeon"
    dungeon_dir.mkdir()
    make_dungeon_file(dungeon_dir, "Id_Dungeon_Crypts_A")
    extracted = tmp_path / "extracted"
    result = run_dungeons(dungeon_dir=dungeon_dir, extracted_root=extracted)
    entity = extracted / "dungeons" / "Id_Dungeon_Crypts_A.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id"] == "Id_Dungeon_Crypts_A"
    assert data["id_tag"] == "Dungeon.Crypts"
    assert "_meta" in data
    index = extracted / "dungeons" / "_index.json"
    assert index.exists()
    assert "Id_Dungeon_Crypts_A" in result
