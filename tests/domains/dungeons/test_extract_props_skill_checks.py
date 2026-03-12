"""Tests for pipeline/domains/dungeons/extract_props_skill_checks.py"""
import json
from pathlib import Path
from pipeline.domains.dungeons.extract_props_skill_checks import extract_props_skill_check, run_props_skill_checks


def make_skill_check_file(tmp_path, check_id):
    data = [{
        "Type": "DCPropsSkillCheckDataAsset",
        "Name": check_id,
        "Properties": {
            "SkillCheckType": "ESkillCheckType::Lockpick",
            "MinDuration": 1.0,
            "MaxDuration": 5.0,
            "MinSkillCheckInterval": 0.5,
            "MaxSkillCheckInterval": 2.0,
        }
    }]
    f = tmp_path / f"{check_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_props_skill_check_returns_id_and_fields(tmp_path):
    f = make_skill_check_file(tmp_path, "Id_PropsSkillCheck_Lockpick")
    result = extract_props_skill_check(f)
    assert result is not None
    assert result["id"] == "Id_PropsSkillCheck_Lockpick"
    assert result["skill_check_type"] == "ESkillCheckType::Lockpick"
    assert result["min_duration"] == 1.0
    assert result["max_duration"] == 5.0
    assert result["min_skill_check_interval"] == 0.5
    assert result["max_skill_check_interval"] == 2.0


def test_extract_props_skill_check_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_props_skill_check(f) is None


def test_run_props_skill_checks_writes_entity_and_index(tmp_path):
    checks_dir = tmp_path / "checks"
    checks_dir.mkdir()
    make_skill_check_file(checks_dir, "Id_PropsSkillCheck_Lockpick")
    extracted = tmp_path / "extracted"
    result = run_props_skill_checks(props_skill_check_dir=checks_dir, extracted_root=extracted)
    entity = extracted / "dungeons" / "Id_PropsSkillCheck_Lockpick.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["skill_check_type"] == "ESkillCheckType::Lockpick"
    assert "_meta" in data
    assert "Id_PropsSkillCheck_Lockpick" in result
