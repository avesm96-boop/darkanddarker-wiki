"""Status domain extractor — run() called by extract_all.py orchestrator."""
from pathlib import Path

from pipeline.domains.status.extract_status_effects import run_status_effects
from pipeline.core.writer import Writer

_V2_BASE = "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2"


def run(raw_root: Path, extracted_root: Path) -> dict:
    """Run all status domain extractors. Returns summary of counts per category.

    NOTE: run_status_effects() writes a partial _index.json on each call.
    This orchestrator overwrites that with a combined index covering all
    4 categories, using the same combined-index pattern as the classes domain.
    """
    print("[status] Starting extraction...")
    summary = {}
    all_effects: dict[str, dict] = {}

    dirs = {
        "player": raw_root / _V2_BASE / "ActorStatus" / "StatusEffect",
        "monster": raw_root / _V2_BASE / "ActorStatusMonster" / "StatusEffect",
        "in_water": raw_root / _V2_BASE / "ActorStatusInWater" / "StatusEffect",
        "item_cosmetic": raw_root / _V2_BASE / "ActorStatusItemCosmetic" / "StatusEffect",
    }

    for category, status_dir in dirs.items():
        if status_dir.exists():
            effects = run_status_effects(
                status_dir=status_dir, category=category, extracted_root=extracted_root
            )
            summary[category] = len(effects)
            all_effects.update(effects)
        else:
            print(f"  [status] WARNING: {status_dir} not found")
            summary[category] = 0

    # Write combined index with ALL categories (overwrites partial indexes
    # written by individual run_status_effects calls above)
    combined_index = [
        {
            "id": v["id"],
            "category": v["category"],
            "event_tag": v.get("event_tag"),
            "asset_tags": v.get("asset_tags"),
        }
        for v in all_effects.values()
    ]
    Writer(extracted_root).write_index("status", combined_index)

    print(f"[status] Done. Summary: {summary}")
    return summary
