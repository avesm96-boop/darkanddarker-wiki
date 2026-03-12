"""Tests for pipeline/domains/dungeons/extract_dungeon_modules.py"""
import json
from pathlib import Path
from pipeline.domains.dungeons.extract_dungeon_modules import extract_dungeon_module, run_dungeon_modules


def make_dungeon_module_file(tmp_path, module_id):
    data = [{
        "Type": "DCDungeonModuleDataAsset",
        "Name": module_id,
        "Properties": {
            "Name": {"LocalizedString": "Crypt Hall"},
            "ModuleType": "EDCDungeonModuleType::Standard",
            "Size": {"X": 3, "Y": 2},
        }
    }]
    f = tmp_path / f"{module_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_dungeon_module_returns_id_and_fields(tmp_path):
    f = make_dungeon_module_file(tmp_path, "Id_DungeonModule_CryptHall")
    result = extract_dungeon_module(f)
    assert result is not None
    assert result["id"] == "Id_DungeonModule_CryptHall"
    assert result["name"] == "Crypt Hall"
    assert result["module_type"] == "EDCDungeonModuleType::Standard"
    assert result["size_x"] == 3
    assert result["size_y"] == 2


def test_extract_dungeon_module_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_dungeon_module(f) is None


def test_run_dungeon_modules_writes_entity_and_index(tmp_path):
    module_dir = tmp_path / "modules"
    module_dir.mkdir()
    make_dungeon_module_file(module_dir, "Id_DungeonModule_CryptHall")
    extracted = tmp_path / "extracted"
    result = run_dungeon_modules(dungeon_module_dir=module_dir, extracted_root=extracted)
    entity = extracted / "dungeons" / "Id_DungeonModule_CryptHall.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["size_x"] == 3
    assert "_meta" in data
    assert "Id_DungeonModule_CryptHall" in result
