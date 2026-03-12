"""Tests for pipeline/domains/combat/extract_projectiles.py"""
import json
from pathlib import Path
from pipeline.domains.combat.extract_projectiles import (
    extract_projectile, run_projectiles
)


def make_projectile_file(tmp_path, proj_id):
    data = [{
        "Type": "DCProjectileDataAsset",
        "Name": proj_id,
        "Properties": {
            "SourceTypes": [
                {"TagName": "Source.Ranged.Arrow"},
                {"TagName": "Source.Ranged.Magic"},
            ],
        }
    }]
    f = tmp_path / f"{proj_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_projectile_returns_id_and_fields(tmp_path):
    f = make_projectile_file(tmp_path, "Id_Projectile_Arrow")
    result = extract_projectile(f)
    assert result is not None
    assert result["id"] == "Id_Projectile_Arrow"
    assert "Source.Ranged.Arrow" in result["source_types"]


def test_extract_projectile_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCGameplayAbilityDataAsset"}]', encoding="utf-8")
    assert extract_projectile(f) is None


def test_run_projectiles_writes_entity_and_index(tmp_path):
    proj_dir = tmp_path / "projectile"
    proj_dir.mkdir()
    make_projectile_file(proj_dir, "Id_Projectile_Arrow")
    extracted = tmp_path / "extracted"
    result = run_projectiles(projectile_dir=proj_dir, extracted_root=extracted)
    entity = extracted / "combat" / "Id_Projectile_Arrow.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert "source_types" in data
    assert "_meta" in data
    index = extracted / "combat" / "_index.json"
    assert index.exists()
    assert "Id_Projectile_Arrow" in result
