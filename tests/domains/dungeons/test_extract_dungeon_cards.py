"""Tests for pipeline/domains/dungeons/extract_dungeon_cards.py"""
import json
from pathlib import Path
from pipeline.domains.dungeons.extract_dungeon_cards import extract_dungeon_card, run_dungeon_cards


def make_dungeon_card_file(tmp_path, card_id):
    data = [{"Type": "DCDungeonCardDataAsset", "Name": card_id}]
    f = tmp_path / f"{card_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_dungeon_card_returns_id(tmp_path):
    f = make_dungeon_card_file(tmp_path, "Id_DungeonCard_Trap")
    result = extract_dungeon_card(f)
    assert result is not None
    assert result["id"] == "Id_DungeonCard_Trap"


def test_extract_dungeon_card_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_dungeon_card(f) is None


def test_run_dungeon_cards_writes_entity_and_index(tmp_path):
    card_dir = tmp_path / "cards"
    card_dir.mkdir()
    make_dungeon_card_file(card_dir, "Id_DungeonCard_Trap")
    extracted = tmp_path / "extracted"
    result = run_dungeon_cards(dungeon_card_dir=card_dir, extracted_root=extracted)
    entity = extracted / "dungeons" / "Id_DungeonCard_Trap.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id"] == "Id_DungeonCard_Trap"
    assert "_meta" in data
    assert "Id_DungeonCard_Trap" in result
