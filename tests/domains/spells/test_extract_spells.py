"""Tests for pipeline/domains/spells/extract_spells.py"""
import json
from pathlib import Path
from pipeline.domains.spells.extract_spells import extract_spell, run_spells


def make_spell_file(tmp_path, spell_id):
    data = [{
        "Type": "DCSpellDataAsset",
        "Name": spell_id,
        "Properties": {
            "Name": {"LocalizedString": "Fireball"},
            "Desc": {"LocalizedString": "Launches a fiery projectile."},
            "CastingType": {"TagName": "Type.Casting.Normal"},
            "SourceType": {"TagName": "Source.Magic.Fire"},
            "CostType": {"TagName": "Type.Cost.Mana"},
            "Range": 800,
            "AreaRadius": 200,
            "SpellTag": {"TagName": "Spell.Fire.Fireball"},
        }
    }]
    f = tmp_path / f"{spell_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_spell_returns_id_and_fields(tmp_path):
    f = make_spell_file(tmp_path, "Id_Spell_Fireball")
    result = extract_spell(f)
    assert result is not None
    assert result["id"] == "Id_Spell_Fireball"
    assert result["name"] == "Fireball"
    assert result["casting_type"] == "Type.Casting.Normal"
    assert result["source_type"] == "Source.Magic.Fire"
    assert result["cost_type"] == "Type.Cost.Mana"
    assert result["range"] == 800
    assert result["area_radius"] == 200
    assert result["spell_tag"] == "Spell.Fire.Fireball"


def test_extract_spell_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "Other"}]', encoding="utf-8")
    assert extract_spell(f) is None


def test_run_spells_writes_entity_and_index(tmp_path):
    spell_dir = tmp_path / "spells"
    spell_dir.mkdir()
    make_spell_file(spell_dir, "Id_Spell_Fireball")
    extracted = tmp_path / "extracted"
    result = run_spells(spell_dir=spell_dir, extracted_root=extracted)
    entity = extracted / "spells" / "Id_Spell_Fireball.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["name"] == "Fireball"
    assert "_meta" in data
    index = extracted / "spells" / "_index.json"
    assert index.exists()
    assert "Id_Spell_Fireball" in result
