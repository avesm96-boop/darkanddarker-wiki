"""Tests for pipeline/domains/dungeons/extract_props_effects.py"""
import json
from pathlib import Path
from pipeline.domains.dungeons.extract_props_effects import extract_props_effect, run_props_effects


def make_props_effect_file(tmp_path, effect_id):
    data = [{
        "Type": "DCGameplayEffectDataAsset",
        "Name": effect_id,
        "Properties": {
            "EventTag": {"TagName": "Effect.Barrel.Explode"},
            "AssetTags": [
                {"TagName": "Tag.Destructible"},
                {"TagName": "Tag.Fire"},
            ],
        }
    }]
    f = tmp_path / f"{effect_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_props_effect_returns_id_and_fields(tmp_path):
    f = make_props_effect_file(tmp_path, "Id_PropsEffect_BarrelExplode")
    result = extract_props_effect(f)
    assert result is not None
    assert result["id"] == "Id_PropsEffect_BarrelExplode"
    assert result["event_tag"] == "Effect.Barrel.Explode"
    assert "Tag.Destructible" in result["asset_tags"]
    assert "Tag.Fire" in result["asset_tags"]


def test_extract_props_effect_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_props_effect(f) is None


def test_run_props_effects_writes_entity_and_index(tmp_path):
    effects_dir = tmp_path / "effects"
    effects_dir.mkdir()
    make_props_effect_file(effects_dir, "Id_PropsEffect_BarrelExplode")
    extracted = tmp_path / "extracted"
    result = run_props_effects(props_effect_dir=effects_dir, extracted_root=extracted)
    entity = extracted / "dungeons" / "Id_PropsEffect_BarrelExplode.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["event_tag"] == "Effect.Barrel.Explode"
    assert "_meta" in data
    assert "Id_PropsEffect_BarrelExplode" in result
