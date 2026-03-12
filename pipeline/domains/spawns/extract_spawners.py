"""Extract DCSpawnerDataAsset files → extracted/spawns/<id>.json + _index.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.writer import Writer


def _extract_asset_id(ref: dict) -> str | None:
    """Extract asset ID from {"AssetPathName": "/Game/.../Foo.Foo", "SubPathString": ""}."""
    if not isinstance(ref, dict):
        return None
    asset_path = ref.get("AssetPathName", "")
    if not asset_path:
        return None
    parts = asset_path.split(".")
    return parts[-1] if len(parts) > 1 else None


def extract_spawner(file_path: Path) -> dict | None:
    """Extract one DCSpawnerDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCSpawnerDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    spawner_items = [
        {
            "spawn_rate": item.get("SpawnRate"),
            "dungeon_grades": item.get("DungeonGrades") or [],
            "loot_drop_group_id": _extract_asset_id(item.get("LootDropGroupId")),
            "monster_id": _extract_asset_id(item.get("MonsterId")),
            "props_id": _extract_asset_id(item.get("PropsId")),
        }
        for item in (props.get("SpawnerItemArray") or [])
    ]

    return {
        "id": obj["Name"],
        "spawner_items": spawner_items,
    }


def run_spawners(spawner_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCSpawnerDataAsset files."""
    files = find_files(str(Path(spawner_dir) / "*.json"))
    print(f"  [spawners] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    spawners = {}

    for f in files:
        result = extract_spawner(f)
        if not result:
            continue
        spawner_id = result["id"]
        spawners[spawner_id] = result
        writer.write_entity("spawns", spawner_id, result, source_files=[str(f)])
        index_entries.append({"id": spawner_id})

    writer.write_index("spawns", index_entries)
    print(f"  [spawners] Extracted {len(spawners)} spawners")
    return spawners
