"""Integration test: run dungeons domain against real raw data."""
import json
from pathlib import Path
import pytest
from pipeline.domains.dungeons import run

RAW_ROOT = Path("raw")
DUNGEON_DIR = RAW_ROOT / "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/Dungeon/Dungeon"


@pytest.mark.skipif(not DUNGEON_DIR.exists(), reason="raw data not present")
def test_dungeons_run_integration(tmp_path):
    summary = run(raw_root=RAW_ROOT, extracted_root=tmp_path)
    assert summary.get("dungeons", 0) > 100
    assert summary.get("dungeon_types", 0) > 10
    assert summary.get("dungeon_grades", 0) > 50
    assert summary.get("dungeon_cards", 0) > 10
    assert summary.get("dungeon_layouts", 0) > 200
    assert summary.get("dungeon_modules", 0) > 200
    assert summary.get("floor_rules", 0) > 50
    assert summary.get("props", 0) > 400
    assert summary.get("props_effects", 0) > 100
    assert summary.get("props_interacts", 0) > 80
    assert summary.get("props_skill_checks", 0) > 0
    assert summary.get("map_icons", 0) > 10
    assert summary.get("vehicles", 0) > 0
    index = tmp_path / "dungeons" / "_index.json"
    assert index.exists()
    index_data = json.loads(index.read_text(encoding="utf-8"))
    entity_types = {e["type"] for e in index_data["entries"]}
    assert "dungeon" in entity_types
    assert "dungeon_type" in entity_types
    assert "dungeon_grade" in entity_types
    assert "prop" in entity_types
    assert "floor_portal" in entity_types
