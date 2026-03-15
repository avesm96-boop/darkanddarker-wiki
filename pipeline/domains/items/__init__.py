"""Items domain extractor — run() called by extract_all.py orchestrator."""
from pathlib import Path

from pipeline.domains.items.extract_item_properties import (
    run_item_property_types,
    build_property_lookup,
)
from pipeline.domains.items.extract_items import run_items

_V2_BASE = "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2"


def run(raw_root: Path, extracted_root: Path) -> dict:
    """Run all items domain extractors. Returns summary of counts."""
    print("[items] Starting extraction...")
    summary = {}

    type_dir = raw_root / _V2_BASE / "ItemProperty" / "ItemPropertyType"
    property_dir = raw_root / _V2_BASE / "ItemProperty" / "ItemProperty"
    item_dir = raw_root / _V2_BASE / "Item" / "Item"

    # 1. Extract property type catalog
    if type_dir.exists():
        property_types = run_item_property_types(type_dir=type_dir, extracted_root=extracted_root)
        summary["item_property_types"] = len(property_types)
    else:
        print(f"  [items] WARNING: {type_dir} not found, skipping property types")
        summary["item_property_types"] = 0

    # 2. Build in-memory property lookup (used to merge into item entity files)
    property_lookup = {}
    if property_dir.exists():
        property_lookup = build_property_lookup(property_dir)
        print(f"  [items] Built property lookup: {len(property_lookup)} items with properties")
    else:
        print(f"  [items] WARNING: {property_dir} not found, items will have no properties")

    # 3. Extract items with merged properties
    if item_dir.exists():
        items = run_items(item_dir=item_dir, extracted_root=extracted_root,
                         property_lookup=property_lookup)
        summary["items"] = len(items)
    else:
        print(f"  [items] WARNING: {item_dir} not found, skipping items")
        summary["items"] = 0

    summary["items_with_properties"] = len(property_lookup)
    print(f"[items] Done. Summary: {summary}")
    return summary
