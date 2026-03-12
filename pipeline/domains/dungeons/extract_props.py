"""Extract DCPropsDataAsset files → extracted/dungeons/<id>.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_tag, resolve_text
from pipeline.core.writer import Writer


def extract_prop(file_path: Path) -> dict | None:
    """Extract one DCPropsDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCPropsDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    return {
        "id": obj["Name"],
        "id_tag": resolve_tag(props.get("IdTag")),
        "name": resolve_text(props.get("Name")),
        "grade_type": resolve_tag(props.get("GradeType")),
        "adv_point": props.get("AdvPoint"),
        "exp_point": props.get("ExpPoint"),
    }


def run_props(props_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCPropsDataAsset files."""
    files = find_files(str(Path(props_dir) / "Id_Props_*.json"))
    print(f"  [props] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    props_map = {}

    for f in files:
        result = extract_prop(f)
        if not result:
            continue
        prop_id = result["id"]
        props_map[prop_id] = result
        writer.write_entity("dungeons", prop_id, result, source_files=[str(f)])
        index_entries.append({"id": prop_id})

    writer.write_index("dungeons", index_entries)
    print(f"  [props] Extracted {len(props_map)} props")
    return props_map
