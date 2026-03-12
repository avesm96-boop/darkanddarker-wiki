"""Tests for pipeline/domains/quests/extract_leaderboards.py"""
import json
from pathlib import Path
from pipeline.domains.quests.extract_leaderboards import extract_leaderboard, run_leaderboards


def make_leaderboard_file(tmp_path, leaderboard_id):
    data = [{"Type": "DCLeaderboardDataAsset", "Name": leaderboard_id, "Properties": {
        "SeasonName": {"Namespace": "DC", "LocalizedString": "Arena Test 1"},
        "LeaderboardType": "EDCLeaderboardType::Arena",
        "LeaderboardSheets": [{"AssetPathName": "/Game/.../Id_LeaderboardSheet_ArenaTrio.Id_LeaderboardSheet_ArenaTrio", "SubPathString": ""}],
        "LeaderboardRanks": [
            {"AssetPathName": "/Game/.../Id_LeaderboardRank_Cadet.Id_LeaderboardRank_Cadet", "SubPathString": ""},
            {"AssetPathName": "/Game/.../Id_LeaderboardRank_Squire.Id_LeaderboardRank_Squire", "SubPathString": ""},
        ],
        "Order": 5,
    }}]
    f = tmp_path / f"{leaderboard_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_leaderboard_returns_id_and_fields(tmp_path):
    f = make_leaderboard_file(tmp_path, "Id_Leaderboard_Arena_Preseason")
    result = extract_leaderboard(f)
    assert result is not None
    assert result["id"] == "Id_Leaderboard_Arena_Preseason"
    assert result["season_name"] == "Arena Test 1"
    assert result["leaderboard_type"] == "Arena"
    assert result["leaderboard_sheets"] == ["Id_LeaderboardSheet_ArenaTrio"]
    assert result["leaderboard_ranks"] == ["Id_LeaderboardRank_Cadet", "Id_LeaderboardRank_Squire"]
    assert result["order"] == 5


def test_extract_leaderboard_handles_empty_arrays(tmp_path):
    data = [{"Type": "DCLeaderboardDataAsset", "Name": "Id_Leaderboard_Empty",
             "Properties": {"LeaderboardSheets": [], "LeaderboardRanks": []}}]
    f = tmp_path / "empty.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    result = extract_leaderboard(f)
    assert result is not None
    assert result["leaderboard_sheets"] == []
    assert result["leaderboard_ranks"] == []


def test_extract_leaderboard_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_leaderboard(f) is None


def test_run_leaderboards_writes_entity_and_index(tmp_path):
    lb_dir = tmp_path / "leaderboards"
    lb_dir.mkdir()
    make_leaderboard_file(lb_dir, "Id_Leaderboard_Arena_Preseason")
    extracted = tmp_path / "extracted"
    result = run_leaderboards(leaderboard_dir=lb_dir, extracted_root=extracted)
    entity = extracted / "quests" / "Id_Leaderboard_Arena_Preseason.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id"] == "Id_Leaderboard_Arena_Preseason"
    assert data["season_name"] == "Arena Test 1"
    assert len(data["leaderboard_ranks"]) == 2
    assert "_meta" in data
    index = extracted / "quests" / "_index.json"
    assert index.exists()
    assert "Id_Leaderboard_Arena_Preseason" in result
