"""Integration test: run combat domain against real raw data."""
import json
from pathlib import Path
import pytest
from pipeline.domains.combat import run

RAW_ROOT = Path("raw")
MELEE_DIR = RAW_ROOT / "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/MeleeAttack/MeleeAttack"


@pytest.mark.skipif(not MELEE_DIR.exists(), reason="raw data not present")
def test_combat_run_integration(tmp_path):
    summary = run(raw_root=RAW_ROOT, extracted_root=tmp_path)
    assert summary.get("melee_attacks", 0) > 100
    assert summary.get("movement_modifiers", 0) > 200
    assert summary.get("ge_modifiers", 0) > 0
    assert summary.get("projectiles", 0) > 50
    assert summary.get("aoes", 0) > 20
    index = tmp_path / "combat" / "_index.json"
    assert index.exists()
    index_data = json.loads(index.read_text(encoding="utf-8"))
    entity_types = {e["type"] for e in index_data["entries"]}
    assert "melee_attack" in entity_types
    assert "movement_modifier" in entity_types
    assert "projectile" in entity_types
    assert "ge_modifier" in entity_types
    assert "aoe" in entity_types
    movement = tmp_path / "combat" / "movement.json"
    assert movement.exists()
    data = json.loads(movement.read_text(encoding="utf-8"))
    assert len(data["modifiers"]) > 10
