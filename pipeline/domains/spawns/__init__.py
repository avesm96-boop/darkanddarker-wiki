"""Spawns domain extractor — run() called by extract_all.py orchestrator."""
from pathlib import Path

from pipeline.domains.spawns.extract_spawners import run_spawners
from pipeline.domains.spawns.extract_loot_drops import run_loot_drops
from pipeline.domains.spawns.extract_loot_drop_groups import run_loot_drop_groups
from pipeline.domains.spawns.extract_loot_drop_rates import run_loot_drop_rates
from pipeline.core.writer import Writer

_V2_BASE = "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2"


def run(raw_root: Path, extracted_root: Path) -> dict:
    """Run all spawns domain extractors. Returns summary of counts."""
    print("[spawns] Starting extraction...")
    summary = {}
    all_entities: dict[str, dict] = {}

    dirs = {
        "spawner":           raw_root / _V2_BASE / "Spawner" / "Spawner",
        "loot_drop":         raw_root / _V2_BASE / "LootDrop" / "LootDrop",
        "loot_drop_group":   raw_root / _V2_BASE / "LootDrop" / "LootDropGroup",
        "loot_drop_rate":    raw_root / _V2_BASE / "LootDrop" / "LootDropRate",
    }

    for key, fn, dir_key, entity_type, param in [
        ("spawners",          run_spawners,          "spawner",         "spawner",          "spawner_dir"),
        ("loot_drops",        run_loot_drops,        "loot_drop",       "loot_drop",        "loot_drop_dir"),
        ("loot_drop_groups",  run_loot_drop_groups,  "loot_drop_group", "loot_drop_group",  "loot_drop_group_dir"),
        ("loot_drop_rates",   run_loot_drop_rates,   "loot_drop_rate",  "loot_drop_rate",   "loot_drop_rate_dir"),
    ]:
        d = dirs[dir_key]
        if d.exists():
            entities = fn(**{param: d, "extracted_root": extracted_root})
            summary[key] = len(entities)
            all_entities.update({k: {**v, "_entity_type": entity_type}
                                  for k, v in entities.items()})
        else:
            print(f"  [spawns] WARNING: {d} not found")
            summary[key] = 0

    # Write combined index (overwrites partial indexes from individual run_* calls)
    combined_index = [
        {"id": v["id"], "type": v["_entity_type"]}
        for v in all_entities.values()
    ]
    Writer(extracted_root).write_index("spawns", combined_index)

    print(f"[spawns] Done. Summary: {summary}")
    return summary
