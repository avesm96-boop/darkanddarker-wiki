"""Extract V2/Constant assets → extracted/engine/constants.json."""
from pathlib import Path

from pipeline.core.reader import load, get_item, get_properties, find_files
from pipeline.core.normalizer import resolve_ref
from pipeline.core.writer import Writer

# Value keys used in real DCConstantDataAsset files (in priority order)
_VALUE_KEYS = ("FloatValue", "Int32Value")


def extract_constant(file_path: Path) -> dict | None:
    """Extract one constant from a DCConstantDataAsset file.

    Real files (FModel export) store the value directly in Properties:
        {"Type": "DCConstantDataAsset", "Name": "Id_Constant_X",
         "Properties": {"FloatValue": 50.0}}

    Synthetic / legacy files may use the Item sub-dict with ConstantId +
    ConstantValue keys.  Both shapes are handled.
    """
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next(
        (o for o in data if isinstance(o, dict) and "Constant" in o.get("Type", "")),
        None,
    )
    if not obj:
        return None

    props = get_properties(obj)

    # --- Try real FModel structure first (FloatValue / Int32Value in Properties) ---
    value = None
    for key in _VALUE_KEYS:
        if key in props:
            value = props[key]
            break

    # --- Fall back to synthetic / legacy Item sub-dict structure ---
    if value is None:
        item = get_item(obj)
        if item:
            const_id_ref = item.get("ConstantId")
            const_id = resolve_ref(const_id_ref) if const_id_ref else None
            value = item.get("ConstantValue")
            return {
                "id": const_id or obj.get("Name", "") or file_path.stem,
                "value": value,
                "source_file": str(file_path),
            }

    # Use the Name field as the constant id (it equals the file stem for real data)
    const_id = obj.get("Name", "") or file_path.stem

    return {
        "id": const_id or file_path.stem,
        "value": value,
        "source_file": str(file_path),
    }


def run_constants(raw_dir: Path, extracted_root: Path) -> dict:
    """Extract all Constant files → extracted/engine/constants.json."""
    print(f"  [constants] Scanning {raw_dir}...")
    files = find_files(str(raw_dir / "Id_Constant_*.json"))
    print(f"  [constants] Found {len(files)} constant files")

    constants = {}
    source_files = []
    for f in files:
        result = extract_constant(f)
        if result:
            constants[result["id"]] = result["value"]
            source_files.append(result["source_file"])

    writer = Writer(extracted_root)
    writer.write_system(
        "engine", "constants", {"constants": constants}, source_files=source_files
    )
    print(f"  [constants] Extracted {len(constants)} constants")
    return constants
