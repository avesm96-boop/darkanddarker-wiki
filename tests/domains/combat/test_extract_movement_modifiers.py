"""Tests for pipeline/domains/combat/extract_movement_modifiers.py"""
import json
from pathlib import Path
from pipeline.domains.combat.extract_movement_modifiers import (
    extract_movement_modifier, run_movement_modifiers
)


def make_mm_file(tmp_path, mm_id, multiply=0.65, jump_z=0.0, gravity=0.0):
    data = [{
        "Type": "DCMovementModifierDataAsset",
        "Name": mm_id,
        "Properties": {
            "Multiply": multiply,
            "JumpZMultiply": jump_z,
            "GravityScaleMultiply": gravity,
        }
    }]
    f = tmp_path / f"{mm_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_movement_modifier_returns_id_and_fields(tmp_path):
    f = make_mm_file(tmp_path, "Id_MovementModifier_Crouch", multiply=0.65)
    result = extract_movement_modifier(f)
    assert result is not None
    assert result["id"] == "Id_MovementModifier_Crouch"
    assert result["multiply"] == 0.65
    assert result["jump_z_multiply"] == 0.0
    assert result["gravity_scale_multiply"] == 0.0


def test_extract_movement_modifier_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "Other"}]', encoding="utf-8")
    assert extract_movement_modifier(f) is None


def test_run_movement_modifiers_writes_entity_and_index(tmp_path):
    mm_dir = tmp_path / "mm"
    mm_dir.mkdir()
    make_mm_file(mm_dir, "Id_MovementModifier_Crouch")
    extracted = tmp_path / "extracted"
    result = run_movement_modifiers(mm_dir=mm_dir, extracted_root=extracted)
    entity = extracted / "combat" / "Id_MovementModifier_Crouch.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["multiply"] == 0.65
    assert "_meta" in data
    index = extracted / "combat" / "_index.json"
    assert index.exists()
    assert "Id_MovementModifier_Crouch" in result


def test_run_movement_modifiers_writes_system_file(tmp_path):
    mm_dir = tmp_path / "mm"
    mm_dir.mkdir()
    make_mm_file(mm_dir, "Id_MovementModifier_Crouch", multiply=0.65)
    make_mm_file(mm_dir, "Id_MovementModifier_Walk", multiply=0.4)
    extracted = tmp_path / "extracted"
    run_movement_modifiers(mm_dir=mm_dir, extracted_root=extracted)
    system_file = extracted / "combat" / "movement.json"
    assert system_file.exists()
    data = json.loads(system_file.read_text(encoding="utf-8"))
    assert "modifiers" in data
    assert "Id_MovementModifier_Crouch" in data["modifiers"]
    assert data["modifiers"]["Id_MovementModifier_Crouch"]["multiply"] == 0.65
    assert "_meta" in data
