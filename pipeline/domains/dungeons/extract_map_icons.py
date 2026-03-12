"""Extract DCMapIconDataAsset files → extracted/dungeons/<id>.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files
from pipeline.core.writer import Writer


def extract_map_icon(file_path: Path) -> dict | None:
    """Extract one DCMapIconDataAsset file. Source data has no Properties."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCMapIconDataAsset"), None)
    if not obj:
        return None

    return {"id": obj["Name"]}


def run_map_icons(map_icon_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCMapIconDataAsset files."""
    files = find_files(str(Path(map_icon_dir) / "Id_MapIcon_*.json"))
    print(f"  [map_icons] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    icons = {}

    for f in files:
        result = extract_map_icon(f)
        if not result:
            continue
        icon_id = result["id"]
        icons[icon_id] = result
        writer.write_entity("dungeons", icon_id, result, source_files=[str(f)])
        index_entries.append({"id": icon_id})

    writer.write_index("dungeons", index_entries)
    print(f"  [map_icons] Extracted {len(icons)} map icons")
    return icons
