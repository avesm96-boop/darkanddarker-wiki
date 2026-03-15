"""Tests for pipeline/domains/classes/extract_perks.py"""
import json
from pathlib import Path
from pipeline.domains.classes.extract_perks import extract_perk, run_perks


def make_perk_file(tmp_path, perk_id, name_str, class_ids):
    classes = [{"PrimaryAssetType": {"Name": "DesignDataPlayerCharacter"},
                "PrimaryAssetName": c} for c in class_ids]
    data = [{
        "Type": "DCPerkDataAsset",
        "Name": perk_id,
        "Properties": {
            "Name": {"Namespace": "DC", "Key": "k", "LocalizedString": name_str},
            "DescData": {"Namespace": "DC", "Key": "d", "LocalizedString": "A perk"},
            "CanUse": True,
            "Classes": classes,
            "Abilities": [],
        }
    }]
    f = tmp_path / f"{perk_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_perk_returns_id_name_and_classes(tmp_path):
    f = make_perk_file(tmp_path, "Id_Perk_AdrenalineSpike", "Adrenaline Spike",
                       ["Id_PlayerCharacter_Fighter"])
    result = extract_perk(f)
    assert result is not None
    assert result["id"] == "Id_Perk_AdrenalineSpike"
    assert result["name"] == "Adrenaline Spike"
    assert "Id_PlayerCharacter_Fighter" in result["classes"]


def test_extract_perk_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "Other"}]', encoding="utf-8")
    assert extract_perk(f) is None


def test_run_perks_writes_entity_and_index(tmp_path):
    perk_dir = tmp_path / "perks"
    perk_dir.mkdir()
    make_perk_file(perk_dir, "Id_Perk_TestPerk", "Test Perk",
                   ["Id_PlayerCharacter_Fighter", "Id_PlayerCharacter_Barbarian"])
    extracted = tmp_path / "extracted"
    result = run_perks(perk_dir=perk_dir, extracted_root=extracted)
    entity = extracted / "classes" / "Id_Perk_TestPerk.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["name"] == "Test Perk"
    assert len(data["classes"]) == 2
    assert "_meta" in data
    assert "Id_Perk_TestPerk" in result
