"""Extract DCDungeonModuleDataAsset files → extracted/dungeons/<id>.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_text
from pipeline.core.writer import Writer


def extract_dungeon_module(file_path: Path) -> dict | None:
    """Extract one DCDungeonModuleDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCDungeonModuleDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    size = props.get("Size") or {}
    return {
        "id": obj["Name"],
        "name": resolve_text(props.get("Name")),
        "module_type": props.get("ModuleType"),
        "size_x": size.get("X"),
        "size_y": size.get("Y"),
    }


def run_dungeon_modules(dungeon_module_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCDungeonModuleDataAsset files."""
    files = find_files(str(Path(dungeon_module_dir) / "Id_DungeonModule_*.json"))
    print(f"  [dungeon_modules] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    modules = {}

    for f in files:
        result = extract_dungeon_module(f)
        if not result:
            continue
        module_id = result["id"]
        modules[module_id] = result
        writer.write_entity("dungeons", module_id, result, source_files=[str(f)])
        index_entries.append({"id": module_id})

    writer.write_index("dungeons", index_entries)
    print(f"  [dungeon_modules] Extracted {len(modules)} dungeon modules")
    return modules
