"""Extract DCBaseGearDataAsset files → extracted/economy/<id>.json + _index.json."""
import logging
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
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


def extract_merchant(file_path: Path) -> dict | None:
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        logger.error("Failed to load merchant file: %s", e)
        return None
    obj = next((o for o in data if isinstance(o, dict) and o.get("Type") == "DCBaseGearDataAsset"), None)
    if not obj:
        return None
    props = get_properties(obj)
    items = [
        {
            "unique_id": item.get("UniqueID"),
            "item_id": _extract_asset_id(item.get("ItemId")),
            "merchant_id": _extract_asset_id(item.get("MerchantId")),
            "required_affinity": item.get("RequiredAffinity"),
        }
        for item in (props.get("BaseGearItemArray") or [])
    ]
    return {"id": obj["Name"], "items": items}


def run_merchants(merchant_dir: Path, extracted_root: Path) -> dict:
    files = find_files(str(Path(merchant_dir) / "*.json"))
    print(f"  [merchants] Found {len(files)} files")
    writer = Writer(extracted_root)
    index_entries = []
    merchants = {}
    for f in files:
        result = extract_merchant(f)
        if not result:
            continue
        mid = result["id"]
        merchants[mid] = result
        writer.write_entity("economy", mid, result, source_files=[str(f)])
        index_entries.append({"id": mid})
    writer.write_index("economy", index_entries)
    print(f"  [merchants] Extracted {len(merchants)} merchants")
    return merchants
