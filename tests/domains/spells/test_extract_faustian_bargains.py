"""Tests for pipeline/domains/spells/extract_faustian_bargains.py"""
import json
from pathlib import Path
from pipeline.domains.spells.extract_faustian_bargains import (
    extract_faustian_bargain, run_faustian_bargains
)


def make_fb_file(tmp_path, fb_id):
    data = [{
        "Type": "DCFaustianBargainDataAsset",
        "Name": fb_id,
        "Properties": {
            "MonsterId": {
                "AssetPathName": "/Game/.../Id_Monster_Lich.Id_Monster_Lich",
                "SubPathString": ""
            },
            "RequiredAffinity": 3,
            "Skills": [
                {"AssetPathName": "/Game/.../Id_Skill_DeathGaze.Id_Skill_DeathGaze", "SubPathString": ""}
            ],
            "Abilities": [],
            "Effects": [],
        }
    }]
    f = tmp_path / f"{fb_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_faustian_bargain_returns_id_and_fields(tmp_path):
    f = make_fb_file(tmp_path, "Id_FaustianBargain_Lich")
    result = extract_faustian_bargain(f)
    assert result is not None
    assert result["id"] == "Id_FaustianBargain_Lich"
    assert result["monster_id"] == "Id_Monster_Lich"
    assert result["required_affinity"] == 3
    assert "Id_Skill_DeathGaze" in result["skills"]


def test_extract_faustian_bargain_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "Other"}]', encoding="utf-8")
    assert extract_faustian_bargain(f) is None


def test_run_faustian_bargains_writes_entity_and_index(tmp_path):
    fb_dir = tmp_path / "fb"
    fb_dir.mkdir()
    make_fb_file(fb_dir, "Id_FaustianBargain_Lich")
    extracted = tmp_path / "extracted"
    result = run_faustian_bargains(fb_dir=fb_dir, extracted_root=extracted)
    entity = extracted / "spells" / "Id_FaustianBargain_Lich.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["monster_id"] == "Id_Monster_Lich"
    assert "_meta" in data
    index = extracted / "spells" / "_index.json"
    assert index.exists()
    assert "Id_FaustianBargain_Lich" in result
