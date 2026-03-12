"""Extract DCParcelDataAsset files → extracted/economy/<id>.json + _index.json."""
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


def extract_parcel(file_path: Path) -> dict | None:
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        logger.error("Failed to load parcel file: %s", e)
        return None
    obj = next((o for o in data if isinstance(o, dict) and o.get("Type") == "DCParcelDataAsset"), None)
    if not obj:
        return None
    props = get_properties(obj)
    parcel_rewards = [
        _extract_asset_id(ref)
        for ref in (props.get("ParcelRewards") or [])
        if _extract_asset_id(ref) is not None
    ]
    return {
        "id": obj["Name"],
        "name": resolve_text(props.get("Name")),
        "flavor_text": resolve_text(props.get("FlavorText")),
        "parcel_rewards": parcel_rewards,
    }


def run_parcels(parcel_dir: Path, extracted_root: Path) -> dict:
    files = find_files(str(Path(parcel_dir) / "*.json"))
    print(f"  [parcels] Found {len(files)} files")
    writer = Writer(extracted_root)
    index_entries = []
    parcels = {}
    for f in files:
        result = extract_parcel(f)
        if not result:
            continue
        pid = result["id"]
        parcels[pid] = result
        writer.write_entity("economy", pid, result, source_files=[str(f)])
        index_entries.append({"id": pid})
    writer.write_index("economy", index_entries)
    print(f"  [parcels] Extracted {len(parcels)} parcels")
    return parcels
