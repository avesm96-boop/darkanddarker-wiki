"""Tests for pipeline/domains/dungeons/extract_dungeon_layouts.py"""
import json
from pathlib import Path
from pipeline.domains.dungeons.extract_dungeon_layouts import extract_dungeon_layout, run_dungeon_layouts


def make_dungeon_layout_file(tmp_path, layout_id):
    data = [{
        "Type": "DCDungeonLayoutDataAsset",
        "Name": layout_id,
        "Properties": {
            "Size": {"X": 2, "Y": 2},
            "Slots": [
                {
                    "SlotTypes": [
                        {
                            "SlotType": "EDCDungeonLayoutSlotType::Normal",
                            "Module": {"AssetPathName": "/Game/.../DM_A.DM_A", "SubPathString": ""},
                            "Rotation": "EDCDungeonModuleRotation::R0",
                        }
                    ]
                },
                {"SlotTypes": []},
                {"SlotTypes": []},
                {"SlotTypes": []},
            ]
        }
    }]
    f = tmp_path / f"{layout_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_dungeon_layout_returns_id_and_fields(tmp_path):
    f = make_dungeon_layout_file(tmp_path, "Id_DungeonLayout_Crypts_001")
    result = extract_dungeon_layout(f)
    assert result is not None
    assert result["id"] == "Id_DungeonLayout_Crypts_001"
    assert result["size_x"] == 2
    assert result["size_y"] == 2
    assert isinstance(result["slots"], list)
    assert len(result["slots"]) == 4
    first_slot = result["slots"][0]
    assert "slot_types" in first_slot
    assert len(first_slot["slot_types"]) == 1
    st = first_slot["slot_types"][0]
    assert st["slot_type"] == "EDCDungeonLayoutSlotType::Normal"
    assert st["module_id"] == "DM_A"
    assert st["rotation"] == "EDCDungeonModuleRotation::R0"


def test_extract_dungeon_layout_handles_null_module(tmp_path):
    data = [{
        "Type": "DCDungeonLayoutDataAsset",
        "Name": "Id_Layout_NoModule",
        "Properties": {
            "Size": {"X": 1, "Y": 1},
            "Slots": [{"SlotTypes": [{"SlotType": "EDCDungeonLayoutSlotType::Normal",
                                      "Module": None, "Rotation": "EDCDungeonModuleRotation::R0"}]}]
        }
    }]
    f = tmp_path / "layout.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    result = extract_dungeon_layout(f)
    assert result is not None
    assert result["slots"][0]["slot_types"][0]["module_id"] is None


def test_extract_dungeon_layout_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_dungeon_layout(f) is None


def test_run_dungeon_layouts_writes_entity_and_index(tmp_path):
    layout_dir = tmp_path / "layouts"
    layout_dir.mkdir()
    make_dungeon_layout_file(layout_dir, "Id_DungeonLayout_Crypts_001")
    extracted = tmp_path / "extracted"
    result = run_dungeon_layouts(dungeon_layout_dir=layout_dir, extracted_root=extracted)
    entity = extracted / "dungeons" / "Id_DungeonLayout_Crypts_001.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["size_x"] == 2
    assert "_meta" in data
    assert "Id_DungeonLayout_Crypts_001" in result
