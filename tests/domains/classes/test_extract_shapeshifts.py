"""Tests for pipeline/domains/classes/extract_shapeshifts.py"""
import json
from pathlib import Path
from pipeline.domains.classes.extract_shapeshifts import extract_shapeshift, run_shapeshifts


def make_shapeshift_file(tmp_path, ss_id, name_str, casting_time=1.0):
    data = [{
        "Type": "DCShapeShiftDataAsset",
        "Name": ss_id,
        "Properties": {
            "Name": {"Namespace": "DC", "Key": "k", "LocalizedString": name_str},
            "Desc": {"Namespace": "DC", "Key": "d", "LocalizedString": "Desc"},
            "CastingTime": casting_time,
            "CapsuleRadiusScale": 2.05,
            "CapsuleHeightScale": 1.0,
            "ShapeShiftTag": {"TagName": "Ability.ShapeShift.Bear"},
            "Classes": [{"PrimaryAssetType": {"Name": "DesignDataPlayerCharacter"},
                         "PrimaryAssetName": "Id_PlayerCharacter_Druid"}],
        }
    }]
    f = tmp_path / f"{ss_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_shapeshift_returns_id_and_fields(tmp_path):
    f = make_shapeshift_file(tmp_path, "Id_ShapeShift_Bear", "Bear", casting_time=1.0)
    result = extract_shapeshift(f)
    assert result is not None
    assert result["id"] == "Id_ShapeShift_Bear"
    assert result["name"] == "Bear"
    assert result["casting_time"] == 1.0
    assert result["shapeshift_tag"] == "Ability.ShapeShift.Bear"
    assert "Id_PlayerCharacter_Druid" in result["classes"]


def test_extract_shapeshift_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "Other"}]', encoding="utf-8")
    assert extract_shapeshift(f) is None


def test_run_shapeshifts_writes_entity_and_index(tmp_path):
    ss_dir = tmp_path / "ss"
    ss_dir.mkdir()
    make_shapeshift_file(ss_dir, "Id_ShapeShift_Panther", "Panther", casting_time=0.5)
    extracted = tmp_path / "extracted"
    result = run_shapeshifts(ss_dir=ss_dir, extracted_root=extracted)
    entity = extracted / "classes" / "Id_ShapeShift_Panther.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["name"] == "Panther"
    assert "_meta" in data
    index = extracted / "classes" / "_index.json"
    assert index.exists()
    assert "Id_ShapeShift_Panther" in result
