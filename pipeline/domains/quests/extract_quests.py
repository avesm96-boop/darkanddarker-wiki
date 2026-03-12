"""Extract DCQuestDataAsset files → extracted/quests/<id>.json + _index.json."""
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


def extract_quest(file_path: Path) -> dict | None:
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        logger.error("Failed to load quest file: %s", e)
        return None
    obj = next((o for o in data if isinstance(o, dict) and o.get("Type") == "DCQuestDataAsset"), None)
    if not obj:
        return None
    props = get_properties(obj)
    return {
        "id": obj["Name"],
        "title_text": resolve_text(props.get("TitleText")),
        "greeting_text": resolve_text(props.get("GreetingText")),
        "complete_text": resolve_text(props.get("CompleteText")),
        "quest_reward": _extract_asset_id(props.get("QuestReward")),
        "quest_contents": [_extract_asset_id(ref) for ref in (props.get("QuestContents") or [])],
        "required_quest": _extract_asset_id(props.get("RequiredQuest")),
        "required_level": props.get("RequiredLevel"),
    }


def run_quests(quest_dir: Path, extracted_root: Path) -> dict:
    files = find_files(str(Path(quest_dir) / "*.json"))
    print(f"  [quests] Found {len(files)} files")
    writer = Writer(extracted_root)
    index_entries = []
    quests = {}
    for f in files:
        result = extract_quest(f)
        if not result:
            continue
        qid = result["id"]
        quests[qid] = result
        writer.write_entity("quests", qid, result, source_files=[str(f)])
        index_entries.append({"id": qid})
    writer.write_index("quests", index_entries)
    print(f"  [quests] Extracted {len(quests)} quests")
    return quests
