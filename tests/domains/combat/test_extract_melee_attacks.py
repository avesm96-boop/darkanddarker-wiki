"""Tests for pipeline/domains/combat/extract_melee_attacks.py"""
import json
from pathlib import Path
from pipeline.domains.combat.extract_melee_attacks import (
    extract_melee_attack, run_melee_attacks
)


def make_melee_file(tmp_path, attack_id):
    data = [{
        "Type": "DCMeleeAttackDataAsset",
        "Name": attack_id,
        "Properties": {
            "HitPlayRate": 1.2,
            "HitPlayRateDuration": 0.5,
            "ComboTypeTag": {"TagName": "ComboType.Sword.Normal"},
            "CanStuckByStaticObject": True,
            "WeakShieldStuckPlayRateDuration": 0.3,
            "StaticObjectStuckPlayRate": 0.8,
        }
    }]
    f = tmp_path / f"{attack_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_melee_attack_returns_id_and_fields(tmp_path):
    f = make_melee_file(tmp_path, "Id_MeleeAttack_GA_ArmingSwordAttack01")
    result = extract_melee_attack(f)
    assert result is not None
    assert result["id"] == "Id_MeleeAttack_GA_ArmingSwordAttack01"
    assert result["hit_play_rate"] == 1.2
    assert result["hit_play_rate_duration"] == 0.5
    assert result["combo_type_tag"] == "ComboType.Sword.Normal"
    assert result["can_stuck_by_static_object"] is True


def test_extract_melee_attack_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "Other"}]', encoding="utf-8")
    assert extract_melee_attack(f) is None


def test_run_melee_attacks_writes_entity_and_index(tmp_path):
    melee_dir = tmp_path / "melee"
    melee_dir.mkdir()
    make_melee_file(melee_dir, "Id_MeleeAttack_GA_ArmingSwordAttack01")
    extracted = tmp_path / "extracted"
    result = run_melee_attacks(melee_dir=melee_dir, extracted_root=extracted)
    entity = extracted / "combat" / "Id_MeleeAttack_GA_ArmingSwordAttack01.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["combo_type_tag"] == "ComboType.Sword.Normal"
    assert "_meta" in data
    index = extracted / "combat" / "_index.json"
    assert index.exists()
    assert "Id_MeleeAttack_GA_ArmingSwordAttack01" in result
