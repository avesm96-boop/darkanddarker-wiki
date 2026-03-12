"""Extract DCDungeonLayoutDataAsset files → extracted/dungeons/<id>.json."""
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


def extract_dungeon_layout(file_path: Path) -> dict | None:
    """Extract one DCDungeonLayoutDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCDungeonLayoutDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    size = props.get("Size") or {}
    slots = [
        {
            "slot_types": [
                {
                    "slot_type": st.get("SlotType"),
                    "module_id": _extract_asset_id(st.get("Module")),
                    "rotation": st.get("Rotation"),
                }
                for st in (slot.get("SlotTypes") or [])
            ]
        }
        for slot in (props.get("Slots") or [])
    ]

    return {
        "id": obj["Name"],
        "size_x": size.get("X"),
        "size_y": size.get("Y"),
        "slots": slots,
    }


def run_dungeon_layouts(dungeon_layout_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCDungeonLayoutDataAsset files."""
    files = find_files(str(Path(dungeon_layout_dir) / "Id_DungeonLayout_*.json"))
    print(f"  [dungeon_layouts] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    layouts = {}

    for f in files:
        result = extract_dungeon_layout(f)
        if not result:
            continue
        layout_id = result["id"]
        layouts[layout_id] = result
        writer.write_entity("dungeons", layout_id, result, source_files=[str(f)])
        index_entries.append({"id": layout_id})

    writer.write_index("dungeons", index_entries)
    print(f"  [dungeon_layouts] Extracted {len(layouts)} dungeon layouts")
    return layouts
