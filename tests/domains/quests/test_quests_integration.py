"""Integration test: run quests domain against real raw data."""
import json
from pathlib import Path
import pytest
from pipeline.domains.quests import run

RAW_ROOT = Path("raw")
QUEST_DIR = RAW_ROOT / "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/Quest/Quest"


@pytest.mark.skipif(not QUEST_DIR.exists(), reason="raw data not present")
def test_quests_run_integration(tmp_path):
    summary = run(raw_root=RAW_ROOT, extracted_root=tmp_path)
    assert summary.get("quests", 0) > 100
    assert summary.get("achievements", 0) > 100
    assert summary.get("triumph_levels", 0) >= 10
    assert summary.get("leaderboards", 0) > 10
    assert summary.get("announces", 0) >= 2
    index = tmp_path / "quests" / "_index.json"
    assert index.exists()
    index_data = json.loads(index.read_text(encoding="utf-8"))
    entity_types = {e["type"] for e in index_data["entries"]}
    assert "quest" in entity_types
    assert "achievement" in entity_types
    assert "triumph_level" in entity_types
    assert "leaderboard" in entity_types
    assert "announce" in entity_types
