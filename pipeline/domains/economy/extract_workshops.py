"""Extract DCWorkshopDataAsset files → extracted/economy/<id>.json + _index.json.

NOTE: All workshop files in the raw data have no Properties — only Type and Name.
extract_workshop() produces {"id": obj["Name"]} and never returns None for a valid
DCWorkshopDataAsset object.
"""
import logging
from pathlib import Path

from pipeline.core.reader import load, find_files
from pipeline.core.writer import Writer

logger = logging.getLogger(__name__)


def extract_workshop(file_path: Path) -> dict | None:
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        logger.error("Failed to load workshop file: %s", e)
        return None
    obj = next((o for o in data if isinstance(o, dict) and o.get("Type") == "DCWorkshopDataAsset"), None)
    if not obj:
        return None
    return {"id": obj["Name"]}


def run_workshops(workshop_dir: Path, extracted_root: Path) -> dict:
    files = find_files(str(Path(workshop_dir) / "*.json"))
    print(f"  [workshops] Found {len(files)} files")
    writer = Writer(extracted_root)
    index_entries = []
    workshops = {}
    for f in files:
        result = extract_workshop(f)
        if not result:
            continue
        wid = result["id"]
        workshops[wid] = result
        writer.write_entity("economy", wid, result, source_files=[str(f)])
        index_entries.append({"id": wid})
    writer.write_index("economy", index_entries)
    print(f"  [workshops] Extracted {len(workshops)} workshops")
    return workshops
