"""Integration test: run spells domain against real raw data."""
import json
from pathlib import Path
import pytest
from pipeline.domains.spells import run

RAW_ROOT = Path("raw")
SPELL_DIR = RAW_ROOT / "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/Spell/Spell"


@pytest.mark.skipif(not SPELL_DIR.exists(), reason="raw data not present")
def test_spells_run_integration(tmp_path):
    summary = run(raw_root=RAW_ROOT, extracted_root=tmp_path)
    assert summary.get("spells", 0) > 50
    assert summary.get("religions", 0) > 10
    assert summary.get("faustian_bargains", 0) > 50
    index = tmp_path / "spells" / "_index.json"
    assert index.exists()
    index_data = json.loads(index.read_text(encoding="utf-8"))
    entity_types = {e["type"] for e in index_data["entries"]}
    assert "spell" in entity_types
    assert "religion" in entity_types
    assert "faustian_bargain" in entity_types
