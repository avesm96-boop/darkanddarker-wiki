"""Tests for pipeline/domains/spawns/extract_loot_drops.py"""
import json
from pathlib import Path
from pipeline.domains.spawns.extract_loot_drops import extract_loot_drop, run_loot_drops


def make_loot_drop_file(tmp_path, drop_id):
    data = [{
        "Type": "DCLootDropDataAsset",
        "Name": drop_id,
        "Properties": {
            "LootDropItemArray": [
                {
                    "ItemId": {"AssetPathName": "/Game/.../Id_Item_Sword.Id_Item_Sword",
                               "SubPathString": ""},
                    "ItemCount": 1,
                    "LuckGrade": 3,
                },
                {
                    "ItemId": {"AssetPathName": "/Game/.../Id_Item_Shield.Id_Item_Shield",
                               "SubPathString": ""},
                    "ItemCount": 2,
                    "LuckGrade": 1,
                },
            ]
        }
    }]
    f = tmp_path / f"{drop_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_loot_drop_returns_id_and_items(tmp_path):
    f = make_loot_drop_file(tmp_path, "ID_Lootdrop_SwordBundle")
    result = extract_loot_drop(f)
    assert result is not None
    assert result["id"] == "ID_Lootdrop_SwordBundle"
    assert isinstance(result["items"], list)
    assert len(result["items"]) == 2
    item = result["items"][0]
    assert item["item_id"] == "Id_Item_Sword"
    assert item["item_count"] == 1
    assert item["luck_grade"] == 3


def test_extract_loot_drop_handles_empty_items(tmp_path):
    data = [{"Type": "DCLootDropDataAsset", "Name": "ID_Lootdrop_Empty",
             "Properties": {"LootDropItemArray": []}}]
    f = tmp_path / "empty.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    result = extract_loot_drop(f)
    assert result is not None
    assert result["items"] == []


def test_extract_loot_drop_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_loot_drop(f) is None


def test_run_loot_drops_writes_entity_and_index(tmp_path):
    drops_dir = tmp_path / "drops"
    drops_dir.mkdir()
    make_loot_drop_file(drops_dir, "ID_Lootdrop_SwordBundle")
    extracted = tmp_path / "extracted"
    result = run_loot_drops(loot_drop_dir=drops_dir, extracted_root=extracted)
    entity = extracted / "spawns" / "ID_Lootdrop_SwordBundle.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id"] == "ID_Lootdrop_SwordBundle"
    assert len(data["items"]) == 2
    assert "_meta" in data
    index = extracted / "spawns" / "_index.json"
    assert index.exists()
    assert "ID_Lootdrop_SwordBundle" in result
