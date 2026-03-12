"""Extract DCDungeonDataAsset files → extracted/dungeons/<id>.json + _index.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_tag, resolve_text
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


def extract_dungeon(file_path: Path) -> dict | None:
    """Extract one DCDungeonDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCDungeonDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    return {
        "id": obj["Name"],
        "id_tag": resolve_tag(props.get("IdTag")),
        "name": resolve_text(props.get("Name")),
        "game_types": props.get("GameTypes") or [],
        "default_dungeon_grade": props.get("DefaultDungeonGrade"),
        "floor": props.get("floor"),
        "floor_rule": _extract_asset_id(props.get("FloorRule")),
        "triumph_exp": props.get("TriumphExp"),
        "module_type": props.get("ModuleType"),
        "fog_enabled": props.get("bFogEnabled"),
        "num_min_escapes": props.get("NumMinEscapes"),
    }


def run_dungeons(dungeon_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCDungeonDataAsset files."""
    files = find_files(str(Path(dungeon_dir) / "Id_Dungeon_*.json"))
    print(f"  [dungeons] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    dungeons = {}

    for f in files:
        result = extract_dungeon(f)
        if not result:
            continue
        dungeon_id = result["id"]
        dungeons[dungeon_id] = result
        writer.write_entity("dungeons", dungeon_id, result, source_files=[str(f)])
        index_entries.append({"id": dungeon_id})

    writer.write_index("dungeons", index_entries)
    print(f"  [dungeons] Extracted {len(dungeons)} dungeons")
    return dungeons
