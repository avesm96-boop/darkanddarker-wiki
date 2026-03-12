"""Extract DCMarketplaceDataAsset files → extracted/economy/<id>.json + _index.json."""
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


def extract_marketplace(file_path: Path) -> dict | None:
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        logger.error("Failed to load marketplace file: %s", e)
        return None
    obj = next((o for o in data if isinstance(o, dict) and o.get("Type") == "DCMarketplaceDataAsset"), None)
    if not obj:
        return None
    props = get_properties(obj)
    base_payments = [
        _extract_asset_id(ref)
        for ref in (props.get("BasePayments") or [])
        if _extract_asset_id(ref) is not None
    ]
    return {
        "id": obj["Name"],
        "name": resolve_text(props.get("Name")),
        "order": props.get("Order"),
        "base_payments": base_payments,
    }


def run_marketplaces(marketplace_dir: Path, extracted_root: Path) -> dict:
    files = find_files(str(Path(marketplace_dir) / "*.json"))
    print(f"  [marketplaces] Found {len(files)} files")
    writer = Writer(extracted_root)
    index_entries = []
    marketplaces = {}
    for f in files:
        result = extract_marketplace(f)
        if not result:
            continue
        mid = result["id"]
        marketplaces[mid] = result
        writer.write_entity("economy", mid, result, source_files=[str(f)])
        index_entries.append({"id": mid})
    writer.write_index("economy", index_entries)
    print(f"  [marketplaces] Extracted {len(marketplaces)} marketplaces")
    return marketplaces
