"""Tests for pipeline/domains/economy/extract_workshops.py"""
import json
from pathlib import Path
from pipeline.domains.economy.extract_workshops import extract_workshop, run_workshops


def make_workshop_file(tmp_path, workshop_id, include_properties=False):
    data = [{"Type": "DCWorkshopDataAsset", "Name": workshop_id}]
    if include_properties:
        data[0]["Properties"] = {}
    f = tmp_path / f"{workshop_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_workshop_returns_id_without_properties(tmp_path):
    f = make_workshop_file(tmp_path, "Id_Workshop_Blacksmith")
    result = extract_workshop(f)
    assert result is not None
    assert result["id"] == "Id_Workshop_Blacksmith"


def test_extract_workshop_returns_id_with_empty_properties(tmp_path):
    f = make_workshop_file(tmp_path, "Id_Workshop_Alchemist", include_properties=True)
    result = extract_workshop(f)
    assert result is not None
    assert result["id"] == "Id_Workshop_Alchemist"


def test_extract_workshop_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_workshop(f) is None


def test_run_workshops_writes_entity_and_index(tmp_path):
    workshop_dir = tmp_path / "workshops"
    workshop_dir.mkdir()
    make_workshop_file(workshop_dir, "Id_Workshop_Blacksmith")
    extracted = tmp_path / "extracted"
    result = run_workshops(workshop_dir=workshop_dir, extracted_root=extracted)
    entity = extracted / "economy" / "Id_Workshop_Blacksmith.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id"] == "Id_Workshop_Blacksmith"
    assert "_meta" in data
    index = extracted / "economy" / "_index.json"
    assert index.exists()
    assert "Id_Workshop_Blacksmith" in result
