"""Tests for pipeline/domains/combat/extract_aoes.py"""
import json
from pathlib import Path
from pipeline.domains.combat.extract_aoes import extract_aoe, run_aoes


def make_aoe_file(tmp_path, aoe_id):
    data = [{
        "Type": "DCAoeDataAsset",
        "Name": aoe_id,
        "Properties": {
            "ArtData": {"AssetPathName": "/Game/.../GA_AoeArt.GA_AoeArt", "SubPathString": ""},
            "SoundData": {"AssetPathName": "/Game/.../GA_AoeSound.GA_AoeSound", "SubPathString": ""},
            "Abilities": [
                {"AssetPathName": "/Game/.../GA_AoeAbility.GA_AoeAbility", "SubPathString": ""}
            ],
        }
    }]
    f = tmp_path / f"{aoe_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_aoe_returns_id_and_fields(tmp_path):
    f = make_aoe_file(tmp_path, "Id_Aoe_IceShardArea")
    result = extract_aoe(f)
    assert result is not None
    assert result["id"] == "Id_Aoe_IceShardArea"
    assert result["art_data"] is not None
    assert result["sound_data"] is not None
    assert isinstance(result["abilities"], list)


def test_extract_aoe_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCGameplayAbilityDataAsset"}]', encoding="utf-8")
    assert extract_aoe(f) is None


def test_run_aoes_writes_entity_and_index(tmp_path):
    aoe_dir = tmp_path / "aoe"
    aoe_dir.mkdir()
    make_aoe_file(aoe_dir, "Id_Aoe_IceShardArea")
    extracted = tmp_path / "extracted"
    result = run_aoes(aoe_dir=aoe_dir, extracted_root=extracted)
    entity = extracted / "combat" / "Id_Aoe_IceShardArea.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert "abilities" in data
    assert "_meta" in data
    index = extracted / "combat" / "_index.json"
    assert index.exists()
    assert "Id_Aoe_IceShardArea" in result
