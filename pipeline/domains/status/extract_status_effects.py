"""Extract DCGameplayEffectDataAsset files → extracted/status/<id>.json + _index.json.

All 4 status subtypes (player, monster, in_water, item_cosmetic) share this extractor.
The 'category' parameter identifies which subtype is being processed.
"""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_tag
from pipeline.core.writer import Writer


def extract_status_effect(file_path: Path, category: str) -> dict | None:
    """Extract one DCGameplayEffectDataAsset file with the given category label."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCGameplayEffectDataAsset"), None)
    if not obj:
        return None

    status_id = obj.get("Name", file_path.stem)
    props = get_properties(obj)

    asset_tags = [
        resolve_tag(t) for t in (props.get("AssetTags") or [])
        if resolve_tag(t) is not None
    ]

    return {
        "id": status_id,
        "category": category,
        "event_tag": resolve_tag(props.get("EventTag")),
        "asset_tags": asset_tags,
        "duration": props.get("Duration"),
        "target_type": resolve_tag(props.get("TargetType")),
    }


def run_status_effects(status_dir: Path, category: str, extracted_root: Path) -> dict:
    """Extract all status effect files → extracted/status/<id>.json + _index.json."""
    files = find_files(str(Path(status_dir) / "*.json"))
    print(f"  [status/{category}] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    effects = {}

    for f in files:
        result = extract_status_effect(f, category=category)
        if not result:
            continue
        status_id = result["id"]
        namespaced_key = f"{category}/{status_id}"
        effects[namespaced_key] = result
        writer.write_entity("status", namespaced_key, result, source_files=[str(f)])
        index_entries.append({
            "id": namespaced_key,
            "category": category,
            "event_tag": result.get("event_tag"),
            "asset_tags": result.get("asset_tags"),
        })

    writer.write_index("status", index_entries)
    print(f"  [status/{category}] Extracted {len(effects)} status effects")
    return effects
