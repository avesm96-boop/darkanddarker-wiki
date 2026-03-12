"""Tests for pipeline/domains/combat/extract_ge_modifiers.py"""
import json
from pathlib import Path
from pipeline.domains.combat.extract_ge_modifiers import (
    extract_ge_modifier, run_ge_modifiers
)


def make_ge_file(tmp_path, ge_id):
    data = [{
        "Type": "DCGEModifierDataAsset",
        "Name": ge_id,
        "Properties": {
            "TargetGameplayEffectTag": {"TagName": "State.ActorStatus.Buff.SacredWater"},
            "EffectType": {"TagName": "Type.GEMod.Source"},
            "Add": 1.5,
        }
    }]
    f = tmp_path / f"{ge_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_ge_modifier_returns_id_and_fields(tmp_path):
    f = make_ge_file(tmp_path, "Id_GEModifier_BrewMaster")
    result = extract_ge_modifier(f)
    assert result is not None
    assert result["id"] == "Id_GEModifier_BrewMaster"
    assert result["target_gameplay_effect_tag"] == "State.ActorStatus.Buff.SacredWater"
    assert result["effect_type"] == "Type.GEMod.Source"
    assert result["add"] == 1.5


def test_extract_ge_modifier_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "Other"}]', encoding="utf-8")
    assert extract_ge_modifier(f) is None


def test_run_ge_modifiers_writes_entity_and_index(tmp_path):
    ge_dir = tmp_path / "ge"
    ge_dir.mkdir()
    make_ge_file(ge_dir, "Id_GEModifier_BrewMaster")
    extracted = tmp_path / "extracted"
    result = run_ge_modifiers(ge_dir=ge_dir, extracted_root=extracted)
    entity = extracted / "combat" / "Id_GEModifier_BrewMaster.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["target_gameplay_effect_tag"] == "State.ActorStatus.Buff.SacredWater"
    assert "_meta" in data
    index = extracted / "combat" / "_index.json"
    assert index.exists()
    assert "Id_GEModifier_BrewMaster" in result
