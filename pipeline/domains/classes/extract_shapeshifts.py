"""Extract DCShapeShiftDataAsset files → extracted/classes/<id>.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_text, resolve_tag
from pipeline.core.writer import Writer


def extract_shapeshift(file_path: Path) -> dict | None:
    """Extract one DCShapeShiftDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCShapeShiftDataAsset"), None)
    if not obj:
        return None

    ss_id = obj.get("Name", file_path.stem)
    props = get_properties(obj)

    classes = []
    for entry in (props.get("Classes") or []):
        if isinstance(entry, dict):
            name = entry.get("PrimaryAssetName")
            if name:
                classes.append(name)

    return {
        "id": ss_id,
        "name": resolve_text(props.get("Name")),
        "description": resolve_text(props.get("Desc")),
        "casting_time": props.get("CastingTime"),
        "capsule_radius_scale": props.get("CapsuleRadiusScale"),
        "capsule_height_scale": props.get("CapsuleHeightScale"),
        "shapeshift_tag": resolve_tag(props.get("ShapeShiftTag")),
        "classes": classes,
    }


def run_shapeshifts(ss_dir: Path, extracted_root: Path) -> dict:
    """Extract all ShapeShift files → extracted/classes/<id>.json."""
    files = find_files(str(Path(ss_dir) / "Id_ShapeShift_*.json"))
    print(f"  [shapeshifts] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    shapeshifts = {}

    for f in files:
        result = extract_shapeshift(f)
        if not result:
            continue
        ss_id = result["id"]
        shapeshifts[ss_id] = result
        writer.write_entity("classes", ss_id, result, source_files=[str(f)])
        index_entries.append({
            "id": ss_id,
            "name": result.get("name"),
            "shapeshift_tag": result.get("shapeshift_tag"),
            "classes": result.get("classes"),
        })

    writer.write_index("classes", index_entries)
    print(f"  [shapeshifts] Extracted {len(shapeshifts)} shapeshifts")
    return shapeshifts
