"""Extract DCLootDropDataAsset files → extracted/spawns/<id>.json + _index.json."""
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


def extract_loot_drop(file_path: Path) -> dict | None:
    """Extract one DCLootDropDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCLootDropDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    items = [
        {
            "item_id": _extract_asset_id(item.get("ItemId")),
            "item_count": item.get("ItemCount"),
            "luck_grade": item.get("LuckGrade"),
        }
        for item in (props.get("LootDropItemArray") or [])
    ]

    return {
        "id": obj["Name"],
        "items": items,
    }


def run_loot_drops(loot_drop_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCLootDropDataAsset files."""
    files = find_files(str(Path(loot_drop_dir) / "*.json"))
    print(f"  [loot_drops] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    drops = {}

    for f in files:
        result = extract_loot_drop(f)
        if not result:
            continue
        drop_id = result["id"]
        drops[drop_id] = result
        writer.write_entity("spawns", drop_id, result, source_files=[str(f)])
        index_entries.append({"id": drop_id})

    writer.write_index("spawns", index_entries)
    print(f"  [loot_drops] Extracted {len(drops)} loot drops")
    return drops
