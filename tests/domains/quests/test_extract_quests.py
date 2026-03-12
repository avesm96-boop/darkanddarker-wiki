"""Tests for pipeline/domains/quests/extract_quests.py"""
import json
from pathlib import Path
from pipeline.domains.quests.extract_quests import extract_quest, run_quests


def make_quest_file(tmp_path, quest_id, required_quest=None, required_level=None):
    props = {}
    if required_quest:
        props["RequiredQuest"] = {"AssetPathName": f"/Game/.../Quest/{required_quest}.{required_quest}", "SubPathString": ""}
    if required_level is not None:
        props["RequiredLevel"] = required_level
    data = [{"Type": "DCQuestDataAsset", "Name": quest_id, "Properties": props}]
    f = tmp_path / f"{quest_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_quest_returns_id_and_fields(tmp_path):
    f = make_quest_file(tmp_path, "Id_Quest_Alchemist_01", required_quest="Id_Quest_Treasurer_06", required_level=114)
    result = extract_quest(f)
    assert result is not None
    assert result["id"] == "Id_Quest_Alchemist_01"
    assert result["required_quest"] == "Id_Quest_Treasurer_06"
    assert result["required_level"] == 114


def test_extract_quest_handles_missing_optional_fields(tmp_path):
    f = make_quest_file(tmp_path, "Id_Quest_Simple_01")
    result = extract_quest(f)
    assert result is not None
    assert result["id"] == "Id_Quest_Simple_01"
    assert result["required_quest"] is None
    assert result["required_level"] is None


def test_extract_quest_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_quest(f) is None


def test_run_quests_writes_entity_and_index(tmp_path):
    quest_dir = tmp_path / "quests"
    quest_dir.mkdir()
    make_quest_file(quest_dir, "Id_Quest_Alchemist_01", required_quest="Id_Quest_Treasurer_06", required_level=114)
    extracted = tmp_path / "extracted"
    result = run_quests(quest_dir=quest_dir, extracted_root=extracted)
    entity = extracted / "quests" / "Id_Quest_Alchemist_01.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id"] == "Id_Quest_Alchemist_01"
    assert data["required_quest"] == "Id_Quest_Treasurer_06"
    assert data["required_level"] == 114
    assert "_meta" in data
    index = extracted / "quests" / "_index.json"
    assert index.exists()
    assert "Id_Quest_Alchemist_01" in result
