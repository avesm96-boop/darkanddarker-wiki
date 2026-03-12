"""Tests for pipeline/domains/spawns/extract_spawners.py"""
import json
from pathlib import Path
from pipeline.domains.spawns.extract_spawners import extract_spawner, run_spawners


def make_spawner_file(tmp_path, spawner_id):
    data = [{
        "Type": "DCSpawnerDataAsset",
        "Name": spawner_id,
        "Properties": {
            "SpawnerItemArray": [
                {
                    "SpawnRate": 0.5,
                    "DungeonGrades": [1, 2, 3],
                    "LootDropGroupId": {
                        "AssetPathName": "/Game/.../LDG_Chest.LDG_Chest", "SubPathString": ""},
                    "MonsterId": {
                        "AssetPathName": "/Game/.../M_Skeleton.M_Skeleton", "SubPathString": ""},
                    "PropsId": None,
                }
            ]
        }
    }]
    f = tmp_path / f"{spawner_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_spawner_returns_id_and_fields(tmp_path):
    f = make_spawner_file(tmp_path, "Id_Spawner_SkeletonChest")
    result = extract_spawner(f)
    assert result is not None
    assert result["id"] == "Id_Spawner_SkeletonChest"
    assert isinstance(result["spawner_items"], list)
    assert len(result["spawner_items"]) == 1
    item = result["spawner_items"][0]
    assert item["spawn_rate"] == 0.5
    assert item["dungeon_grades"] == [1, 2, 3]
    assert item["loot_drop_group_id"] == "LDG_Chest"
    assert item["monster_id"] == "M_Skeleton"
    assert item["props_id"] is None


def test_extract_spawner_handles_empty_items(tmp_path):
    data = [{"Type": "DCSpawnerDataAsset", "Name": "Id_Spawner_Empty",
             "Properties": {"SpawnerItemArray": []}}]
    f = tmp_path / "empty.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    result = extract_spawner(f)
    assert result is not None
    assert result["spawner_items"] == []


def test_extract_spawner_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_spawner(f) is None


def test_run_spawners_writes_entity_and_index(tmp_path):
    spawner_dir = tmp_path / "spawners"
    spawner_dir.mkdir()
    make_spawner_file(spawner_dir, "Id_Spawner_SkeletonChest")
    extracted = tmp_path / "extracted"
    result = run_spawners(spawner_dir=spawner_dir, extracted_root=extracted)
    entity = extracted / "spawns" / "Id_Spawner_SkeletonChest.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id"] == "Id_Spawner_SkeletonChest"
    assert isinstance(data["spawner_items"], list)
    assert "_meta" in data
    index = extracted / "spawns" / "_index.json"
    assert index.exists()
    assert "Id_Spawner_SkeletonChest" in result
