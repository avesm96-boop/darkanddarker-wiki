"""Monsters domain extractor — run() called by extract_all.py orchestrator."""
from pathlib import Path

from pipeline.domains.monsters.extract_monsters import run_monsters

_V2_BASE = "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2"


def run(raw_root: Path, extracted_root: Path) -> dict:
    """Run the monsters domain extractor. Returns summary of counts."""
    print("[monsters] Starting extraction...")
    summary = {}

    monster_dir = raw_root / _V2_BASE / "Monster" / "Monster"
    if monster_dir.exists():
        monsters = run_monsters(monster_dir=monster_dir, extracted_root=extracted_root)
        summary["monsters"] = len(monsters)
    else:
        print(f"  [monsters] WARNING: {monster_dir} not found")
        summary["monsters"] = 0

    print(f"[monsters] Done. Summary: {summary}")
    return summary
