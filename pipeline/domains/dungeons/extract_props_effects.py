"""Extract DCGameplayEffectDataAsset (Props/PropsEffect/) → extracted/dungeons/<id>.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_tag
from pipeline.core.writer import Writer


def extract_props_effect(file_path: Path) -> dict | None:
    """Extract one DCGameplayEffectDataAsset file from Props/PropsEffect/.

    NOTE: Only EventTag and AssetTags are present in this sub-directory.
    Duration and TargetType (present in status domain) are absent here.
    """
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCGameplayEffectDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    return {
        "id": obj["Name"],
        "event_tag": resolve_tag(props.get("EventTag")),
        "asset_tags": [
            resolve_tag(t) for t in (props.get("AssetTags") or [])
            if resolve_tag(t) is not None
        ],
    }


def run_props_effects(props_effect_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCGameplayEffectDataAsset files from Props/PropsEffect/."""
    files = find_files(str(Path(props_effect_dir) / "*.json"))
    print(f"  [props_effects] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    effects = {}

    for f in files:
        result = extract_props_effect(f)
        if not result:
            continue
        effect_id = result["id"]
        effects[effect_id] = result
        writer.write_entity("dungeons", effect_id, result, source_files=[str(f)])
        index_entries.append({"id": effect_id})

    writer.write_index("dungeons", index_entries)
    print(f"  [props_effects] Extracted {len(effects)} props effects")
    return effects
