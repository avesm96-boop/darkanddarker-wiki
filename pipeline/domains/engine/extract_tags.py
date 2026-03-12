"""Extract tag group assets → extracted/engine/tags.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files
from pipeline.core.writer import Writer

# Map UE5 Type → output key
TAG_TYPE_MAP = {
    "IdTagGroup": "id_tag_groups",
    "AbilityRelationshipTagGroup": "ability_relationship_tag_groups",
    "GameplayCueTagGroup": "gameplay_cue_tag_groups",
    "GameplayEffectRelationTagGroup": "gameplay_effect_relation_tag_groups",
    "TagMessageRelationshipTagGroup": "tag_message_relationship_tag_groups",
    "InteractSettingGroup": "interact_setting_groups",
}


def run_tags(raw_dirs: list[Path], extracted_root: Path) -> dict:
    """Extract all tag group assets → extracted/engine/tags.json."""
    groups: dict[str, list] = {v: [] for v in TAG_TYPE_MAP.values()}
    source_files = []

    for raw_dir in raw_dirs:
        for json_file in find_files(str(Path(raw_dir) / "*.json")):
            try:
                data = load(json_file)
            except (FileNotFoundError, ValueError):
                continue
            obj = next((o for o in data if isinstance(o, dict)
                        and TAG_TYPE_MAP.get(o.get("Type", ""))), None)
            if obj is None:
                continue
            output_key = TAG_TYPE_MAP[obj.get("Type", "")]
            tags = obj.get("Properties", {}).get("Tags") or []
            tag_names = [t.get("TagName", t) if isinstance(t, dict) else t for t in tags]
            groups[output_key].append({
                "name": obj.get("Name", ""),
                "tags": tag_names,
                "source_file": str(json_file),
            })
            source_files.append(str(json_file))

    writer = Writer(extracted_root)
    writer.write_system("engine", "tags", groups, source_files=source_files)
    total = sum(len(v) for v in groups.values())
    print(f"  [tags] Extracted {total} tag group entries")
    return groups
