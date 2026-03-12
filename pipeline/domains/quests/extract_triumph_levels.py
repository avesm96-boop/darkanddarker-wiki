"""Extract DCTriumphLevelDataAsset files → extracted/quests/<id>.json + _index.json."""
import logging
from pathlib import Path

from pipeline.core.reader import load, find_files
from pipeline.core.writer import Writer

logger = logging.getLogger(__name__)


def extract_triumph_level(file_path: Path) -> dict | None:
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        logger.error("Failed to load triumph level file: %s", e)
        return None
    obj = next((o for o in data if isinstance(o, dict) and o.get("Type") == "DCTriumphLevelDataAsset"), None)
    if not obj:
        return None
    return {"id": obj["Name"]}


def run_triumph_levels(triumph_level_dir: Path, extracted_root: Path) -> dict:
    files = find_files(str(Path(triumph_level_dir) / "*.json"))
    print(f"  [triumph_levels] Found {len(files)} files")
    writer = Writer(extracted_root)
    index_entries = []
    triumph_levels = {}
    for f in files:
        result = extract_triumph_level(f)
        if not result:
            continue
        tid = result["id"]
        triumph_levels[tid] = result
        writer.write_entity("quests", tid, result, source_files=[str(f)])
        index_entries.append({"id": tid})
    writer.write_index("quests", index_entries)
    print(f"  [triumph_levels] Extracted {len(triumph_levels)} triumph levels")
    return triumph_levels
