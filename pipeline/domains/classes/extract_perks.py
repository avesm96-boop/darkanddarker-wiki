"""Extract DCPerkDataAsset files → extracted/classes/<id>.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_text
from pipeline.core.writer import Writer


def _extract_class_ids(classes_list: list) -> list[str]:
    """Extract PrimaryAssetName strings from the Classes array."""
    result = []
    for entry in (classes_list or []):
        if isinstance(entry, dict):
            name = entry.get("PrimaryAssetName")
            if name:
                result.append(name)
    return result


def extract_perk(file_path: Path) -> dict | None:
    """Extract one DCPerkDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCPerkDataAsset"), None)
    if not obj:
        return None

    perk_id = obj.get("Name", file_path.stem)
    props = get_properties(obj)

    return {
        "id": perk_id,
        "name": resolve_text(props.get("Name")),
        "description": resolve_text(props.get("DescData")),
        "can_use": props.get("CanUse", True),
        "classes": _extract_class_ids(props.get("Classes")),
    }


def run_perks(perk_dir: Path, extracted_root: Path) -> dict:
    """Extract all Perk files → extracted/classes/<id>.json entries."""
    files = find_files(str(Path(perk_dir) / "Id_Perk_*.json"))
    print(f"  [perks] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    perks = {}

    for f in files:
        result = extract_perk(f)
        if not result:
            continue
        perk_id = result["id"]
        perks[perk_id] = result
        writer.write_entity("classes", perk_id, result, source_files=[str(f)])
        index_entries.append({
            "id": perk_id,
            "name": result.get("name"),
            "classes": result.get("classes"),
        })

    writer.write_index("classes", index_entries)
    print(f"  [perks] Extracted {len(perks)} perks")
    return perks
