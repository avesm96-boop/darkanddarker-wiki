"""Extract DCLootDropGroupDataAsset files → extracted/spawns/<id>.json + _index.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.writer import Writer


def _extract_asset_id(ref: dict) -> str | None:
    if not isinstance(ref, dict):
        return None
    asset_path = ref.get("AssetPathName", "")
    if not asset_path:
        return None
    parts = asset_path.split(".")
    return parts[-1] if len(parts) > 1 else None


def extract_loot_drop_group(file_path: Path) -> dict | None:
    """Extract one DCLootDropGroupDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCLootDropGroupDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    items = [
        {
            "dungeon_grade": item.get("DungeonGrade"),
            "loot_drop_id": _extract_asset_id(item.get("LootDropId")),
            "loot_drop_rate_id": _extract_asset_id(item.get("LootDropRateId")),
            "loot_drop_count": item.get("LootDropCount"),
        }
        for item in (props.get("LootDropGroupItemArray") or [])
    ]

    return {
        "id": obj["Name"],
        "items": items,
    }


def run_loot_drop_groups(loot_drop_group_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCLootDropGroupDataAsset files."""
    files = find_files(str(Path(loot_drop_group_dir) / "*.json"))
    print(f"  [loot_drop_groups] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    groups = {}

    for f in files:
        result = extract_loot_drop_group(f)
        if not result:
            continue
        group_id = result["id"]
        groups[group_id] = result
        writer.write_entity("spawns", group_id, result, source_files=[str(f)])
        index_entries.append({"id": group_id})

    writer.write_index("spawns", index_entries)
    print(f"  [loot_drop_groups] Extracted {len(groups)} loot drop groups")
    return groups
