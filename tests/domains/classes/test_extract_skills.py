"""Tests for pipeline/domains/classes/extract_skills.py"""
import json
from pathlib import Path
from pipeline.domains.classes.extract_skills import extract_skill, run_skills


def make_skill_file(tmp_path, skill_id, name_str, skill_type_tag, tier=1):
    data = [{
        "Type": "DCSkillDataAsset",
        "Name": skill_id,
        "Properties": {
            "Name": {"Namespace": "DC", "Key": "k", "LocalizedString": name_str},
            "DescData": {"Namespace": "DC", "Key": "d", "LocalizedString": "Desc"},
            "SkillType": {"TagName": skill_type_tag},
            "SkillTier": tier,
            "UseMoving": True,
            "Classes": [{"PrimaryAssetType": {"Name": "DesignDataPlayerCharacter"},
                         "PrimaryAssetName": "Id_PlayerCharacter_Barbarian"}],
        }
    }]
    f = tmp_path / f"{skill_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_skill_returns_id_name_and_type(tmp_path):
    f = make_skill_file(tmp_path, "Id_Skill_AchillesStrike", "Achilles Strike",
                        "Type.Skill.Instant", tier=1)
    result = extract_skill(f)
    assert result is not None
    assert result["id"] == "Id_Skill_AchillesStrike"
    assert result["name"] == "Achilles Strike"
    assert result["skill_type"] == "Type.Skill.Instant"
    assert result["skill_tier"] == 1


def test_extract_skill_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "Other"}]', encoding="utf-8")
    assert extract_skill(f) is None


def test_run_skills_writes_entity_and_index(tmp_path):
    skill_dir = tmp_path / "skills"
    skill_dir.mkdir()
    make_skill_file(skill_dir, "Id_Skill_TestSkill", "Test Skill", "Type.Skill.Toggle")
    extracted = tmp_path / "extracted"
    result = run_skills(skill_dir=skill_dir, extracted_root=extracted)
    entity = extracted / "classes" / "Id_Skill_TestSkill.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["name"] == "Test Skill"
    assert "_meta" in data
    assert "Id_Skill_TestSkill" in result
