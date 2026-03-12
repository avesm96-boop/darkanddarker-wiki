"""Tests for pipeline/domains/dungeons/extract_dungeon_grades.py"""
import json
from pathlib import Path
from pipeline.domains.dungeons.extract_dungeon_grades import extract_dungeon_grade, run_dungeon_grades


def make_dungeon_grade_file(tmp_path, grade_id):
    data = [{
        "Type": "DCDungeonGradeDataAsset",
        "Name": grade_id,
        "Properties": {
            "DungeonIdTag": {"TagName": "DungeonGrade.Normal"},
            "GearPoolIndex": 3,
        }
    }]
    f = tmp_path / f"{grade_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_dungeon_grade_returns_id_and_fields(tmp_path):
    f = make_dungeon_grade_file(tmp_path, "Id_DungeonGrade_Normal")
    result = extract_dungeon_grade(f)
    assert result is not None
    assert result["id"] == "Id_DungeonGrade_Normal"
    assert result["dungeon_id_tag"] == "DungeonGrade.Normal"
    assert result["gear_pool_index"] == 3


def test_extract_dungeon_grade_handles_missing_id_tag(tmp_path):
    data = [{"Type": "DCDungeonGradeDataAsset", "Name": "Id_DungeonGrade_NoTag",
             "Properties": {"GearPoolIndex": 1}}]
    f = tmp_path / "grade.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    result = extract_dungeon_grade(f)
    assert result is not None
    assert result["dungeon_id_tag"] is None
    assert result["gear_pool_index"] == 1


def test_extract_dungeon_grade_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_dungeon_grade(f) is None


def test_run_dungeon_grades_writes_entity_and_index(tmp_path):
    grade_dir = tmp_path / "grades"
    grade_dir.mkdir()
    make_dungeon_grade_file(grade_dir, "Id_DungeonGrade_Normal")
    extracted = tmp_path / "extracted"
    result = run_dungeon_grades(dungeon_grade_dir=grade_dir, extracted_root=extracted)
    entity = extracted / "dungeons" / "Id_DungeonGrade_Normal.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["dungeon_id_tag"] == "DungeonGrade.Normal"
    assert "_meta" in data
    assert "Id_DungeonGrade_Normal" in result
