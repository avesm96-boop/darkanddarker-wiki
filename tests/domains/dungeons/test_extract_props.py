"""Tests for pipeline/domains/dungeons/extract_props.py"""
import json
from pathlib import Path
from pipeline.domains.dungeons.extract_props import extract_prop, run_props


def make_prop_file(tmp_path, prop_id):
    data = [{
        "Type": "DCPropsDataAsset",
        "Name": prop_id,
        "Properties": {
            "IdTag": {"TagName": "Props.Barrel"},
            "Name": {"LocalizedString": "Barrel"},
            "GradeType": {"TagName": "Grade.Common"},
            "AdvPoint": 5,
            "ExpPoint": 10,
        }
    }]
    f = tmp_path / f"{prop_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_prop_returns_id_and_fields(tmp_path):
    f = make_prop_file(tmp_path, "Id_Props_Barrel")
    result = extract_prop(f)
    assert result is not None
    assert result["id"] == "Id_Props_Barrel"
    assert result["id_tag"] == "Props.Barrel"
    assert result["name"] == "Barrel"
    assert result["grade_type"] == "Grade.Common"
    assert result["adv_point"] == 5
    assert result["exp_point"] == 10


def test_extract_prop_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_prop(f) is None


def test_run_props_writes_entity_and_index(tmp_path):
    props_dir = tmp_path / "props"
    props_dir.mkdir()
    make_prop_file(props_dir, "Id_Props_Barrel")
    extracted = tmp_path / "extracted"
    result = run_props(props_dir=props_dir, extracted_root=extracted)
    entity = extracted / "dungeons" / "Id_Props_Barrel.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id_tag"] == "Props.Barrel"
    assert "_meta" in data
    assert "Id_Props_Barrel" in result
