"""Tests for pipeline/domains/monsters/extract_monsters.py"""
import json
from pathlib import Path
from pipeline.domains.monsters.extract_monsters import extract_monster, run_monsters


def make_monster_file(tmp_path, monster_id, id_tag, class_type, grade_type, adv=50, exp=8):
    data = [{
        "Type": "DCMonsterDataAsset",
        "Name": monster_id,
        "Properties": {
            "IdTag": {"TagName": id_tag},
            "ClassType": {"TagName": class_type},
            "GradeType": {"TagName": grade_type},
            "CharacterTypes": [{"TagName": "Type.Character.Undead.Skeleton"}],
            "AdvPoint": adv,
            "ExpPoint": exp,
        }
    }]
    f = tmp_path / f"{monster_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_monster_returns_id_and_fields(tmp_path):
    f = make_monster_file(
        tmp_path, "Id_Monster_Skeleton_Common",
        "Id.Monster.Skeleton", "Type.Monster.Class.Normal",
        "Type.Monster.Grade.Common", adv=5, exp=2
    )
    result = extract_monster(f)
    assert result is not None
    assert result["id"] == "Id_Monster_Skeleton_Common"
    assert result["id_tag"] == "Id.Monster.Skeleton"
    assert result["class_type"] == "Type.Monster.Class.Normal"
    assert result["grade_type"] == "Type.Monster.Grade.Common"
    assert result["adv_point"] == 5
    assert result["exp_point"] == 2
    assert "Type.Character.Undead.Skeleton" in result["character_types"]


def test_extract_monster_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "Other"}]', encoding="utf-8")
    assert extract_monster(f) is None


def test_run_monsters_writes_entity_and_index(tmp_path):
    mon_dir = tmp_path / "monsters"
    mon_dir.mkdir()
    make_monster_file(mon_dir, "Id_Monster_Skeleton_Common",
                      "Id.Monster.Skeleton", "Type.Monster.Class.Normal",
                      "Type.Monster.Grade.Common")
    extracted = tmp_path / "extracted"
    result = run_monsters(monster_dir=mon_dir, extracted_root=extracted)
    entity = extracted / "monsters" / "Id_Monster_Skeleton_Common.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id_tag"] == "Id.Monster.Skeleton"
    assert "_meta" in data
    index = extracted / "monsters" / "_index.json"
    assert index.exists()
    assert "Id_Monster_Skeleton_Common" in result
