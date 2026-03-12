"""Tests for pipeline/domains/spawns/extract_loot_drop_groups.py"""
import json
from pathlib import Path
from pipeline.domains.spawns.extract_loot_drop_groups import extract_loot_drop_group, run_loot_drop_groups


def make_loot_drop_group_file(tmp_path, group_id):
    data = [{
        "Type": "DCLootDropGroupDataAsset",
        "Name": group_id,
        "Properties": {
            "LootDropGroupItemArray": [
                {
                    "DungeonGrade": 2,
                    "LootDropId": {
                        "AssetPathName": "/Game/.../ID_Lootdrop_Swords.ID_Lootdrop_Swords",
                        "SubPathString": ""},
                    "LootDropRateId": {
                        "AssetPathName": "/Game/.../LDR_Common.LDR_Common",
                        "SubPathString": ""},
                    "LootDropCount": 3,
                }
            ]
        }
    }]
    f = tmp_path / f"{group_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_loot_drop_group_returns_id_and_items(tmp_path):
    f = make_loot_drop_group_file(tmp_path, "LDG_WeaponBundle")
    result = extract_loot_drop_group(f)
    assert result is not None
    assert result["id"] == "LDG_WeaponBundle"
    assert isinstance(result["items"], list)
    assert len(result["items"]) == 1
    item = result["items"][0]
    assert item["dungeon_grade"] == 2
    assert item["loot_drop_id"] == "ID_Lootdrop_Swords"
    assert item["loot_drop_rate_id"] == "LDR_Common"
    assert item["loot_drop_count"] == 3


def test_extract_loot_drop_group_handles_empty_items(tmp_path):
    data = [{"Type": "DCLootDropGroupDataAsset", "Name": "LDG_Empty",
             "Properties": {"LootDropGroupItemArray": []}}]
    f = tmp_path / "empty.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    result = extract_loot_drop_group(f)
    assert result is not None
    assert result["items"] == []


def test_extract_loot_drop_group_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_loot_drop_group(f) is None


def test_run_loot_drop_groups_writes_entity_and_index(tmp_path):
    groups_dir = tmp_path / "groups"
    groups_dir.mkdir()
    make_loot_drop_group_file(groups_dir, "LDG_WeaponBundle")
    extracted = tmp_path / "extracted"
    result = run_loot_drop_groups(loot_drop_group_dir=groups_dir, extracted_root=extracted)
    entity = extracted / "spawns" / "LDG_WeaponBundle.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id"] == "LDG_WeaponBundle"
    assert len(data["items"]) == 1
    assert "_meta" in data
    index = extracted / "spawns" / "_index.json"
    assert index.exists()
    assert "LDG_WeaponBundle" in result
