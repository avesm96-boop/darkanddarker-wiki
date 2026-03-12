"""Extract DCPropsSkillCheckDataAsset files → extracted/dungeons/<id>.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.writer import Writer


def extract_props_skill_check(file_path: Path) -> dict | None:
    """Extract one DCPropsSkillCheckDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCPropsSkillCheckDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    return {
        "id": obj["Name"],
        "skill_check_type": props.get("SkillCheckType"),
        "min_duration": props.get("MinDuration"),
        "max_duration": props.get("MaxDuration"),
        "min_skill_check_interval": props.get("MinSkillCheckInterval"),
        "max_skill_check_interval": props.get("MaxSkillCheckInterval"),
    }


def run_props_skill_checks(props_skill_check_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCPropsSkillCheckDataAsset files."""
    files = find_files(str(Path(props_skill_check_dir) / "*.json"))
    print(f"  [props_skill_checks] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    checks = {}

    for f in files:
        result = extract_props_skill_check(f)
        if not result:
            continue
        check_id = result["id"]
        checks[check_id] = result
        writer.write_entity("dungeons", check_id, result, source_files=[str(f)])
        index_entries.append({"id": check_id})

    writer.write_index("dungeons", index_entries)
    print(f"  [props_skill_checks] Extracted {len(checks)} props skill checks")
    return checks
