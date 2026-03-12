"""Tests for pipeline/domains/quests/extract_achievements.py"""
import json
from pathlib import Path
from pipeline.domains.quests.extract_achievements import extract_achievement, run_achievements


def make_achievement_file(tmp_path, achievement_id):
    data = [{"Type": "DCAchievementDataAsset", "Name": achievement_id, "Properties": {
        "Enable": True,
        "ListingOrder": 139,
        "MainCategory": "EDCAchievementMainCategory::Arena",
        "MainCategoryText": {"Namespace": "DC", "LocalizedString": "Arena"},
        "Name": {"Namespace": "DC", "LocalizedString": "First Blood"},
        "Description": {"Namespace": "DC", "LocalizedString": "Win an Arena match for the first time."},
        "ObjectiveId": [{"AssetPathName": "/Game/.../Objective_GameResult_12.Objective_GameResult_12", "SubPathString": ""}],
        "SequenceGroupOrder": 1,
        "SequenceGroup": "EDCAchievementSequenceGroup::Achievement_Group_Arena_Win",
        "ArtData": {"AssetPathName": "/Game/.../WinningArena.WinningArena", "SubPathString": ""},
    }}]
    f = tmp_path / f"{achievement_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_achievement_returns_id_and_fields(tmp_path):
    f = make_achievement_file(tmp_path, "Achievement_Arena_01")
    result = extract_achievement(f)
    assert result is not None
    assert result["id"] == "Achievement_Arena_01"
    assert result["enabled"] is True
    assert result["listing_order"] == 139
    assert result["main_category"] == "Arena"
    assert result["main_category_text"] == "Arena"
    assert result["name"] == "First Blood"
    assert result["description"] == "Win an Arena match for the first time."
    assert result["objective_ids"] == ["Objective_GameResult_12"]
    assert result["sequence_group_order"] == 1
    assert result["sequence_group"] == "Achievement_Group_Arena_Win"
    assert result["art_data"] == "WinningArena"


def test_extract_achievement_handles_empty_objective_ids(tmp_path):
    data = [{"Type": "DCAchievementDataAsset", "Name": "Achievement_Empty_01",
             "Properties": {"Enable": False, "ObjectiveId": []}}]
    f = tmp_path / "empty.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    result = extract_achievement(f)
    assert result is not None
    assert result["objective_ids"] == []


def test_extract_achievement_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_achievement(f) is None


def test_run_achievements_writes_entity_and_index(tmp_path):
    achievement_dir = tmp_path / "achievements"
    achievement_dir.mkdir()
    make_achievement_file(achievement_dir, "Achievement_Arena_01")
    extracted = tmp_path / "extracted"
    result = run_achievements(achievement_dir=achievement_dir, extracted_root=extracted)
    entity = extracted / "quests" / "Achievement_Arena_01.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id"] == "Achievement_Arena_01"
    assert data["name"] == "First Blood"
    assert data["objective_ids"] == ["Objective_GameResult_12"]
    assert "_meta" in data
    index = extracted / "quests" / "_index.json"
    assert index.exists()
    assert "Achievement_Arena_01" in result
