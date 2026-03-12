"""Integration test: run economy domain against real raw data."""
import json
from pathlib import Path
import pytest
from pipeline.domains.economy import run

RAW_ROOT = Path("raw")
MERCHANT_DIR = RAW_ROOT / "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/Merchant/BaseGear"


@pytest.mark.skipif(not MERCHANT_DIR.exists(), reason="raw data not present")
def test_economy_run_integration(tmp_path):
    summary = run(raw_root=RAW_ROOT, extracted_root=tmp_path)
    assert summary.get("merchants", 0) > 0
    assert summary.get("marketplaces", 0) > 0
    assert summary.get("parcels", 0) > 0
    assert summary.get("workshops", 0) > 0
    index = tmp_path / "economy" / "_index.json"
    assert index.exists()
    index_data = json.loads(index.read_text(encoding="utf-8"))
    entity_types = {e["type"] for e in index_data["entries"]}
    assert "merchant" in entity_types
    assert "marketplace" in entity_types
    assert "parcel" in entity_types
    assert "workshop" in entity_types
