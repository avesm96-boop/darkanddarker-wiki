"""Extract DCReligionDataAsset files → extracted/spells/<id>.json + _index.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_text
from pipeline.core.writer import Writer


def extract_religion(file_path: Path) -> dict | None:
    """Extract one DCReligionDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCReligionDataAsset"), None)
    if not obj:
        return None

    religion_id = obj.get("Name", file_path.stem)
    props = get_properties(obj)

    return {
        "id": religion_id,
        "name": resolve_text(props.get("Name")),
        "description": resolve_text(props.get("Desc")),
        "subtitle": resolve_text(props.get("Subtitle")),
        "offering_cost": props.get("OfferingCost"),
        "order": props.get("Order"),
    }


def run_religions(religion_dir: Path, extracted_root: Path) -> dict:
    """Extract all Religion files → extracted/spells/<id>.json + _index.json.

    NOTE: religion_dir should point to V2/Religion/Religion/ (base type only).
    The parent V2/Religion/ directory contains 4 other types which are out of scope.
    """
    files = find_files(str(Path(religion_dir) / "*.json"))
    print(f"  [religions] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    religions = {}

    for f in files:
        result = extract_religion(f)
        if not result:
            continue
        religion_id = result["id"]
        religions[religion_id] = result
        writer.write_entity("spells", religion_id, result, source_files=[str(f)])
        index_entries.append({
            "id": religion_id,
            "name": result.get("name"),
            "order": result.get("order"),
        })

    writer.write_index("spells", index_entries)
    print(f"  [religions] Extracted {len(religions)} religions")
    return religions
