"""Extract UserDefinedEnum assets from raw/ → extracted/engine/enums.json."""
import json
import sys
from pathlib import Path

from pipeline.core.reader import find_by_type, load
from pipeline.core.writer import Writer


def extract_enum_from_file(file_path: Path) -> dict | None:
    """Extract enum name and values from a UserDefinedEnum file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return None

    enum_obj = next((obj for obj in data
                     if isinstance(obj, dict) and obj.get("Type") == "UserDefinedEnum"), None)
    if not enum_obj:
        return None

    enum_name = enum_obj.get("Name")
    if not enum_name:
        return None

    # Build display name lookup from DisplayNameMap
    display_names = {}
    for entry in enum_obj.get("Properties", {}).get("DisplayNameMap", []):
        key = entry.get("Key")
        val = entry.get("Value", {}).get("CultureInvariantString", "")
        if key:
            display_names[key] = val

    # Extract enum values, skip _MAX sentinel
    values = []
    for full_name, index in enum_obj.get("Names", {}).items():
        parts = full_name.split("::")
        if len(parts) != 2:
            continue
        member = parts[1]
        if member == "_MAX":
            continue
        values.append({
            "index": index,
            "name": member,
            "displayName": display_names.get(member, member),
        })

    values.sort(key=lambda v: v["index"])
    return {"name": enum_name, "values": values}


def run_enums(raw_dir: Path, extracted_root: Path) -> dict:
    """Extract all UserDefinedEnum files. Returns {enum_name: {values: [...]}}."""
    print(f"  [enums] Scanning {raw_dir}...")
    enum_files = find_by_type("UserDefinedEnum", raw_dir)
    print(f"  [enums] Found {len(enum_files)} enum files")

    enums_data = {}
    for file_path in enum_files:
        result = extract_enum_from_file(file_path)
        if result:
            enums_data[result["name"]] = {"values": result["values"]}

    writer = Writer(extracted_root)
    # enums.json is a system file (not entity-per-enum)
    writer.write_system("engine", "enums", enums_data,
                        source_files=[str(f) for f in enum_files])
    print(f"  [enums] Extracted {len(enums_data)} enums")
    return enums_data
