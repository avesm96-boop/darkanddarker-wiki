"""Economy domain extractor — run() called by extract_all.py orchestrator."""
from pathlib import Path

from pipeline.domains.economy.extract_merchants import run_merchants
from pipeline.domains.economy.extract_marketplaces import run_marketplaces
from pipeline.domains.economy.extract_parcels import run_parcels
from pipeline.domains.economy.extract_workshops import run_workshops
from pipeline.core.writer import Writer

_V2_BASE = "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2"


def run(raw_root: Path, extracted_root: Path) -> dict:
    """Run all economy domain extractors. Returns summary of counts.

    NOTE: Individual run_* functions each write a partial _index.json as a
    side-effect (useful for standalone runs / unit tests). This orchestrator
    overwrites that partial index with a single combined index containing all
    entity types at the end.
    """
    print("[economy] Starting extraction...")
    summary = {}
    all_entities: dict[str, dict] = {}

    dirs = {
        "merchant":    raw_root / _V2_BASE / "Merchant" / "BaseGear",
        "marketplace": raw_root / _V2_BASE / "Marketplace" / "Marketplace",
        "parcel":      raw_root / _V2_BASE / "Parcel" / "Parcel",
        "workshop":    raw_root / _V2_BASE / "Workshop" / "Workshop",
    }

    for key, fn, dir_key, entity_type, param in [
        ("merchants",    run_merchants,    "merchant",    "merchant",    "merchant_dir"),
        ("marketplaces", run_marketplaces, "marketplace", "marketplace", "marketplace_dir"),
        ("parcels",      run_parcels,      "parcel",      "parcel",      "parcel_dir"),
        ("workshops",    run_workshops,    "workshop",    "workshop",    "workshop_dir"),
    ]:
        d = dirs[dir_key]
        if d.exists():
            entities = fn(**{param: d, "extracted_root": extracted_root})
            summary[key] = len(entities)
            all_entities.update({k: {**v, "_entity_type": entity_type} for k, v in entities.items()})
        else:
            print(f"  [economy] WARNING: {d} not found")
            summary[key] = 0

    # Write combined index (overwrites partial indexes from individual run_* calls)
    combined_index = [{"id": v["id"], "type": v["_entity_type"]} for v in all_entities.values()]
    Writer(extracted_root).write_index("economy", combined_index)

    print(f"[economy] Done. Summary: {summary}")
    return summary
