"""Extract DCLeaderboardDataAsset files → extracted/quests/<id>.json + _index.json."""
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


def extract_leaderboard(file_path: Path) -> dict | None:
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        logger.error("Failed to load leaderboard file: %s", e)
        return None
    obj = next((o for o in data if isinstance(o, dict) and o.get("Type") == "DCLeaderboardDataAsset"), None)
    if not obj:
        return None
    props = get_properties(obj)
    return {
        "id": obj["Name"],
        "season_name": resolve_text(props.get("SeasonName")),
        "leaderboard_type": _strip_enum(props.get("LeaderboardType")),
        "leaderboard_sheets": [_extract_asset_id(ref) for ref in (props.get("LeaderboardSheets") or [])],
        "leaderboard_ranks": [_extract_asset_id(ref) for ref in (props.get("LeaderboardRanks") or [])],
        "order": props.get("Order"),
    }


def run_leaderboards(leaderboard_dir: Path, extracted_root: Path) -> dict:
    files = find_files(str(Path(leaderboard_dir) / "*.json"))
    print(f"  [leaderboards] Found {len(files)} files")
    writer = Writer(extracted_root)
    index_entries = []
    leaderboards = {}
    for f in files:
        result = extract_leaderboard(f)
        if not result:
            continue
        lid = result["id"]
        leaderboards[lid] = result
        writer.write_entity("quests", lid, result, source_files=[str(f)])
        index_entries.append({"id": lid})
    writer.write_index("quests", index_entries)
    print(f"  [leaderboards] Extracted {len(leaderboards)} leaderboards")
    return leaderboards
