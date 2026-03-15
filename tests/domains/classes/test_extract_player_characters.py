"""Tests for pipeline/domains/classes/extract_player_characters.py"""
import json
from pathlib import Path
from pipeline.domains.classes.extract_player_characters import (
    extract_player_character, run_player_characters
)


def make_pc_file(tmp_path, pc_id, stats):
    data = [{
        "Type": "DCGameplayEffectDataAsset",
        "Name": pc_id,
        "Properties": stats
    }]
    f = tmp_path / f"{pc_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_player_character_returns_id_and_base_stats(tmp_path):
    f = make_pc_file(tmp_path, "Id_PlayerCharacterEffect_Barbarian", {
        "StrengthBase": 20, "VigorBase": 25, "AgilityBase": 13,
        "DexterityBase": 12, "WillBase": 12, "KnowledgeBase": 8,
        "ResourcefulnessBase": 9, "MoveSpeedBase": 300,
    })
    result = extract_player_character(f)
    assert result is not None
    assert result["id"] == "Id_PlayerCharacterEffect_Barbarian"
    assert result["strength_base"] == 20
    assert result["vigor_base"] == 25
    assert result["move_speed_base"] == 300


def test_extract_player_character_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "Other"}]', encoding="utf-8")
    assert extract_player_character(f) is None


def test_run_player_characters_writes_entity_and_index(tmp_path):
    pc_dir = tmp_path / "pcs"
    pc_dir.mkdir()
    make_pc_file(pc_dir, "Id_PlayerCharacterEffect_Fighter", {
        "StrengthBase": 15, "VigorBase": 20, "AgilityBase": 14,
        "DexterityBase": 14, "WillBase": 15, "KnowledgeBase": 12,
        "ResourcefulnessBase": 10, "MoveSpeedBase": 300,
    })
    extracted = tmp_path / "extracted"
    result = run_player_characters(pc_dir=pc_dir, extracted_root=extracted)
    entity = extracted / "classes" / "Id_PlayerCharacterEffect_Fighter.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["strength_base"] == 15
    assert "_meta" in data
    index = extracted / "classes" / "_index.json"
    assert index.exists()
    assert "Id_PlayerCharacterEffect_Fighter" in result
