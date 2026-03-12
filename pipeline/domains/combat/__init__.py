"""Combat domain extractor — run() called by extract_all.py orchestrator."""
from pathlib import Path

_V2_BASE = "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2"


def run(raw_root: Path, extracted_root: Path) -> dict:
    """Run all combat domain extractors. Returns summary of counts."""
    print("[combat] Starting extraction...")
    summary = {}
    print(f"[combat] Done. Summary: {summary}")
    return summary
