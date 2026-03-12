"""Extract DCAnnounceDataAsset files → extracted/quests/<id>.json + _index.json."""
import logging
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_text
from pipeline.core.writer import Writer

logger = logging.getLogger(__name__)


def extract_announce(file_path: Path) -> dict | None:
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        logger.error("Failed to load announce file: %s", e)
        return None
    obj = next((o for o in data if isinstance(o, dict) and o.get("Type") == "DCAnnounceDataAsset"), None)
    if not obj:
        return None
    props = get_properties(obj)
    return {
        "id": obj["Name"],
        "announce_text": resolve_text(props.get("AnnounceText")),
    }


def run_announces(announce_dir: Path, extracted_root: Path) -> dict:
    files = find_files(str(Path(announce_dir) / "*.json"))
    print(f"  [announces] Found {len(files)} files")
    writer = Writer(extracted_root)
    index_entries = []
    announces = {}
    for f in files:
        result = extract_announce(f)
        if not result:
            continue
        aid = result["id"]
        announces[aid] = result
        writer.write_entity("quests", aid, result, source_files=[str(f)])
        index_entries.append({"id": aid})
    writer.write_index("quests", index_entries)
    print(f"  [announces] Extracted {len(announces)} announces")
    return announces
