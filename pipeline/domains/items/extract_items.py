"""Extract DCItemDataAsset files → extracted/items/<id>.json + _index.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_text, resolve_tag
from pipeline.core.writer import Writer


def extract_item(file_path: Path, property_lookup: dict | None = None) -> dict | None:
    """Extract one DCItemDataAsset file into a normalized dict."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCItemDataAsset"), None)
    if not obj:
        return None

    item_id = obj.get("Name", file_path.stem)
    props = get_properties(obj)

    # Strip EItemType:: prefix (e.g. "EItemType::Armor" → "Armor")
    raw_item_type = props.get("ItemType", "")
    item_type = raw_item_type.split("::")[-1] if "::" in raw_item_type else raw_item_type

    result: dict = {
        "id": item_id,
        "name": resolve_text(props.get("Name")),
        "flavor_text": resolve_text(props.get("FlavorText")),
        "item_type": item_type,
        "slot_type": resolve_tag(props.get("SlotType")),
        "armor_type": resolve_tag(props.get("ArmorType")),
        "rarity_type": resolve_tag(props.get("RarityType")),
        "max_count": props.get("MaxCount", 1),
        "can_drop": props.get("CanDrop", True),
        "inventory_width": props.get("InventoryWidth", 1),
        "inventory_height": props.get("InventoryHeight", 1),
    }

    if property_lookup and item_id in property_lookup:
        result["properties"] = property_lookup[item_id]

    return result


def run_items(item_dir: Path, extracted_root: Path,
              property_lookup: dict | None = None) -> dict:
    """Extract all Item files → extracted/items/<id>.json + _index.json."""
    files = find_files(str(Path(item_dir) / "Id_Item_*.json"))
    print(f"  [items] Found {len(files)} item files")

    writer = Writer(extracted_root)
    index_entries = []
    items = {}

    for f in files:
        result = extract_item(f, property_lookup)
        if not result:
            continue
        item_id = result["id"]
        items[item_id] = result
        writer.write_entity("items", item_id, result, source_files=[str(f)])
        index_entries.append({
            "id": item_id,
            "name": result.get("name"),
            "item_type": result.get("item_type"),
            "slot_type": result.get("slot_type"),
            "rarity_type": result.get("rarity_type"),
        })

    writer.write_index("items", index_entries)
    print(f"  [items] Extracted {len(items)} items")
    return items
