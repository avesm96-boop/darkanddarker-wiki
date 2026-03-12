"""Integration test: run status domain against real raw data."""
import json
from pathlib import Path
import pytest
from pipeline.domains.status import run

RAW_ROOT = Path("raw")
ACTOR_STATUS_DIR = RAW_ROOT / "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/ActorStatus/StatusEffect"


@pytest.mark.skipif(not ACTOR_STATUS_DIR.exists(), reason="raw data not present")
def test_status_run_integration(tmp_path):
    summary = run(raw_root=RAW_ROOT, extracted_root=tmp_path)
    assert summary.get("player", 0) > 500
    assert summary.get("monster", 0) > 100
    assert summary.get("in_water", 0) > 0
    assert summary.get("item_cosmetic", 0) > 0
    index = tmp_path / "status" / "_index.json"
    assert index.exists()
    data = json.loads(index.read_text(encoding="utf-8"))
    # Combined index should have entries from all 4 categories
    categories = {e["category"] for e in data["entries"]}
    assert "player" in categories
    assert "monster" in categories
    assert "in_water" in categories
    assert "item_cosmetic" in categories
