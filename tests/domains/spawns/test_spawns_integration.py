"""Integration test: run spawns domain against real raw data."""
import json
from pathlib import Path
import pytest
from pipeline.domains.spawns import run

RAW_ROOT = Path("raw")
SPAWNER_DIR = RAW_ROOT / "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/Spawner/Spawner"


@pytest.mark.skipif(not SPAWNER_DIR.exists(), reason="raw data not present")
def test_spawns_run_integration(tmp_path):
    summary = run(raw_root=RAW_ROOT, extracted_root=tmp_path)
    assert summary.get("spawners", 0) > 400
    assert summary.get("loot_drops", 0) > 300
    assert summary.get("loot_drop_groups", 0) > 300
    assert summary.get("loot_drop_rates", 0) > 2000
    index = tmp_path / "spawns" / "_index.json"
    assert index.exists()
    index_data = json.loads(index.read_text(encoding="utf-8"))
    entity_types = {e["type"] for e in index_data["entries"]}
    assert "spawner" in entity_types
    assert "loot_drop" in entity_types
    assert "loot_drop_group" in entity_types
    assert "loot_drop_rate" in entity_types
