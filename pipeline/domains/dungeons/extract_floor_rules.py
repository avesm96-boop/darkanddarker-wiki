"""Extract floor rule assets → extracted/dungeons/<id>.json.

Handles three types in one file:
  DCFloorPortalDataAsset      → FloorRule/FloorPortal/
  DCFloorRuleBlizzardDataAsset → FloorRule/FloorRuleBlizzard/
  DCFloorRuleDeathSwarmDataAsset → FloorRule/FloorRuleDeathSwarm/
"""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.writer import Writer


def extract_floor_portal(file_path: Path) -> dict | None:
    """Extract one DCFloorPortalDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCFloorPortalDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    return {
        "id": obj["Name"],
        "portal_type": props.get("PortalType"),
        "portal_scroll_num": props.get("PortalScrollNum"),
    }


def extract_floor_rule_blizzard(file_path: Path) -> dict | None:
    """Extract one DCFloorRuleBlizzardDataAsset file. Minimal/no properties in source data."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCFloorRuleBlizzardDataAsset"), None)
    if not obj:
        return None

    return {"id": obj["Name"]}


def extract_floor_rule_deathswarm(file_path: Path) -> dict | None:
    """Extract one DCFloorRuleDeathSwarmDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCFloorRuleDeathSwarmDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    return {
        "id": obj["Name"],
        "floor_rule_items": props.get("FloorRuleItemArray") or [],
    }


def run_floor_rules(floor_rule_dir: Path, extracted_root: Path) -> dict:
    """Extract all floor rule assets from sub-directories.

    Scans FloorPortal/, FloorRuleBlizzard/, FloorRuleDeathSwarm/ under floor_rule_dir.
    Tags each entity with _entity_type. Returns combined {id: entity} dict.
    """
    floor_rule_dir = Path(floor_rule_dir)
    writer = Writer(extracted_root)
    all_rules = {}

    extractors = [
        ("FloorPortal", extract_floor_portal, "floor_portal"),
        ("FloorRuleBlizzard", extract_floor_rule_blizzard, "floor_rule_blizzard"),
        ("FloorRuleDeathSwarm", extract_floor_rule_deathswarm, "floor_rule_deathswarm"),
    ]

    for subdir, extractor, entity_type in extractors:
        subdir_path = floor_rule_dir / subdir
        if not subdir_path.exists():
            print(f"  [floor_rules] WARNING: {subdir_path} not found")
            continue
        files = find_files(str(subdir_path / "*.json"))
        print(f"  [floor_rules/{subdir}] Found {len(files)} files")
        for f in files:
            result = extractor(f)
            if not result:
                continue
            rule_id = result["id"]
            tagged = {**result, "_entity_type": entity_type}
            all_rules[rule_id] = tagged
            writer.write_entity("dungeons", rule_id, result, source_files=[str(f)])

    writer.write_index("dungeons", [{"id": v["id"]} for v in all_rules.values()])
    print(f"  [floor_rules] Extracted {len(all_rules)} floor rules total")
    return all_rules
