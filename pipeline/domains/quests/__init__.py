"""Quests domain extractor — run() called by extract_all.py orchestrator."""
from pathlib import Path

from pipeline.domains.quests.extract_quests import run_quests
from pipeline.domains.quests.extract_achievements import run_achievements
from pipeline.domains.quests.extract_triumph_levels import run_triumph_levels
from pipeline.domains.quests.extract_leaderboards import run_leaderboards
from pipeline.domains.quests.extract_announces import run_announces
from pipeline.core.writer import Writer

_V2_BASE = "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2"


def run(raw_root: Path, extracted_root: Path) -> dict:
    """Run all quests domain extractors. Returns summary of counts.

    NOTE: Individual run_* functions each write a partial _index.json as a
    side-effect (useful for standalone runs / unit tests). This orchestrator
    overwrites that partial index with a single combined index containing all
    entity types at the end.
    """
    print("[quests] Starting extraction...")
    summary = {}
    all_entities: dict[str, dict] = {}

    dirs = {
        "quest":         raw_root / _V2_BASE / "Quest" / "Quest",
        "achievement":   raw_root / _V2_BASE / "Achievement" / "Achievement",
        "triumph_level": raw_root / _V2_BASE / "TriumphLevel" / "TriumphLevel",
        "leaderboard":   raw_root / _V2_BASE / "Leaderboard" / "Leaderboard",
        "announce":      raw_root / _V2_BASE / "Announce" / "Announce",
    }

    for key, fn, dir_key, entity_type, param in [
        ("quests",         run_quests,         "quest",         "quest",         "quest_dir"),
        ("achievements",   run_achievements,   "achievement",   "achievement",   "achievement_dir"),
        ("triumph_levels", run_triumph_levels, "triumph_level", "triumph_level", "triumph_level_dir"),
        ("leaderboards",   run_leaderboards,   "leaderboard",   "leaderboard",   "leaderboard_dir"),
        ("announces",      run_announces,      "announce",      "announce",      "announce_dir"),
    ]:
        d = dirs[dir_key]
        if d.exists():
            entities = fn(**{param: d, "extracted_root": extracted_root})
            summary[key] = len(entities)
            all_entities.update({k: {**v, "_entity_type": entity_type} for k, v in entities.items()})
        else:
            print(f"  [quests] WARNING: {d} not found")
            summary[key] = 0

    combined_index = [{"id": v["id"], "type": v["_entity_type"]} for v in all_entities.values()]
    Writer(extracted_root).write_index("quests", combined_index)

    print(f"[quests] Done. Summary: {summary}")
    return summary
