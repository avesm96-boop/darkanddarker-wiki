"""Extract DCAchievementDataAsset files → extracted/quests/<id>.json + _index.json."""
import logging
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_text
from pipeline.core.writer import Writer

logger = logging.getLogger(__name__)


def _extract_asset_id(ref: dict) -> str | None:
    if not isinstance(ref, dict):
        return None
    asset_path = ref.get("AssetPathName", "")
    if not asset_path:
        return None
    parts = asset_path.split(".")
    return parts[-1] if len(parts) > 1 else None


def _strip_enum(val: str | None) -> str | None:
    if val and "::" in val:
        return val.split("::")[-1]
    return val


def extract_achievement(file_path: Path) -> dict | None:
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        logger.error("Failed to load achievement file: %s", e)
        return None
    obj = next((o for o in data if isinstance(o, dict) and o.get("Type") == "DCAchievementDataAsset"), None)
    if not obj:
        return None
    props = get_properties(obj)
    return {
        "id": obj["Name"],
        "enabled": props.get("Enable", False),  # UE5 key is "Enable"; absent means disabled
        "listing_order": props.get("ListingOrder"),
        "main_category": _strip_enum(props.get("MainCategory")),
        "main_category_text": resolve_text(props.get("MainCategoryText")),
        "display_name": resolve_text(props.get("Name")),
        "description": resolve_text(props.get("Description")),
        "objective_ids": [_extract_asset_id(ref) for ref in (props.get("ObjectiveId") or [])],
        "sequence_group_order": props.get("SequenceGroupOrder"),
        "sequence_group": _strip_enum(props.get("SequenceGroup")),
        "art_data": _extract_asset_id(props.get("ArtData")),
    }


def run_achievements(achievement_dir: Path, extracted_root: Path) -> dict:
    files = find_files(str(Path(achievement_dir) / "*.json"))
    print(f"  [achievements] Found {len(files)} files")
    writer = Writer(extracted_root)
    index_entries = []
    achievements = {}
    for f in files:
        result = extract_achievement(f)
        if not result:
            continue
        aid = result["id"]
        achievements[aid] = result
        writer.write_entity("quests", aid, result, source_files=[str(f)])
        index_entries.append({"id": aid})
    writer.write_index("quests", index_entries)
    print(f"  [achievements] Extracted {len(achievements)} achievements")
    return achievements
