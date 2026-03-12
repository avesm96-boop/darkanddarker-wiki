"""Tests for pipeline/domains/spells/extract_religions.py"""
import json
from pathlib import Path
from pipeline.domains.spells.extract_religions import extract_religion, run_religions


def make_religion_file(tmp_path, religion_id):
    data = [{
        "Type": "DCReligionDataAsset",
        "Name": religion_id,
        "Properties": {
            "Name": {"LocalizedString": "Blythar"},
            "Desc": {"LocalizedString": "God of chaos."},
            "Subtitle": {"LocalizedString": "The Chaotic One"},
            "OfferingCost": 50,
            "Order": 1,
        }
    }]
    f = tmp_path / f"{religion_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_religion_returns_id_and_fields(tmp_path):
    f = make_religion_file(tmp_path, "Id_DesignDataReligion_Blythar")
    result = extract_religion(f)
    assert result is not None
    assert result["id"] == "Id_DesignDataReligion_Blythar"
    assert result["name"] == "Blythar"
    assert result["description"] == "God of chaos."
    assert result["subtitle"] == "The Chaotic One"
    assert result["offering_cost"] == 50
    assert result["order"] == 1


def test_extract_religion_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCReligionBlessingDataAsset"}]', encoding="utf-8")
    assert extract_religion(f) is None


def test_run_religions_writes_entity_and_index(tmp_path):
    religion_dir = tmp_path / "religions"
    religion_dir.mkdir()
    make_religion_file(religion_dir, "Id_DesignDataReligion_Blythar")
    extracted = tmp_path / "extracted"
    result = run_religions(religion_dir=religion_dir, extracted_root=extracted)
    entity = extracted / "spells" / "Id_DesignDataReligion_Blythar.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["name"] == "Blythar"
    assert "_meta" in data
    index = extracted / "spells" / "_index.json"
    assert index.exists()
    assert "Id_DesignDataReligion_Blythar" in result
