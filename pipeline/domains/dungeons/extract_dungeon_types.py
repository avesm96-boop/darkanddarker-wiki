"""Extract DCDungeonTypeDataAsset files → extracted/dungeons/<id>.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_tag, resolve_text
from pipeline.core.writer import Writer


def extract_dungeon_type(file_path: Path) -> dict | None:
    """Extract one DCDungeonTypeDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCDungeonTypeDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    return {
        "id": obj["Name"],
        "id_tag": resolve_tag(props.get("IdTag")),
        "name": resolve_text(props.get("Name")),
        "group_name": resolve_text(props.get("GroupName")),
        "chapter_name": resolve_text(props.get("ChapterName")),
        "desc": resolve_text(props.get("Desc")),
        "order": props.get("Order"),
    }


def run_dungeon_types(dungeon_type_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCDungeonTypeDataAsset files."""
    files = find_files(str(Path(dungeon_type_dir) / "Id_DungeonType_*.json"))
    print(f"  [dungeon_types] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    types = {}

    for f in files:
        result = extract_dungeon_type(f)
        if not result:
            continue
        type_id = result["id"]
        types[type_id] = result
        writer.write_entity("dungeons", type_id, result, source_files=[str(f)])
        index_entries.append({"id": type_id})

    writer.write_index("dungeons", index_entries)
    print(f"  [dungeon_types] Extracted {len(types)} dungeon types")
    return types
