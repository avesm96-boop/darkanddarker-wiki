"""Integration test: run quests domain against real raw data."""
import json
from pathlib import Path
import pytest
from pipeline.domains.quests import run

RAW_ROOT = Path("raw")
QUEST_DIR = RAW_ROOT / "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/Quest/Quest"


@pytest.mark.skipif(not QUEST_DIR.exists(), reason="raw data not present")
def test_quests_run_integration(tmp_path):
    summary = run(raw_root=RAW_ROOT, extracted_root=tmp_path)
    assert summary.get("quests", 0) > 100
    assert summary.get("achievements", 0) > 100
    assert summary.get("triumph_levels", 0) >= 10
    assert summary.get("leaderboards", 0) > 10
    assert summary.get("announces", 0) >= 2
    index = tmp_path / "quests" / "_index.json"
    assert index.exists()
    index_data = json.loads(index.read_text(encoding="utf-8"))
    entity_types = {e["type"] for e in index_data["entries"]}
    assert "quest" in entity_types
    assert "achievement" in entity_types
    assert "triumph_level" in entity_types
    assert "leaderboard" in entity_types
    assert "announce" in entity_types


@pytest.mark.skipif(not QUEST_DIR.exists(), reason="raw data not present")
def test_quest_entity_structure(tmp_path):
    """Spot-check: a quest entity must have the required keys."""
    run(raw_root=RAW_ROOT, extracted_root=tmp_path)
    quest_files = sorted((tmp_path / "quests").glob("Id_Quest_*.json"))
    assert quest_files, "expected at least one quest entity file"
    entity = json.loads(quest_files[0].read_text(encoding="utf-8"))
    for key in ("id", "title_text", "greeting_text", "complete_text",
                "quest_reward", "quest_contents", "required_quest", "required_level"):
        assert key in entity, f"quest entity missing key: {key}"


@pytest.mark.skipif(not QUEST_DIR.exists(), reason="raw data not present")
def test_achievement_entity_structure(tmp_path):
    """Spot-check: an achievement entity must have the required keys."""
    run(raw_root=RAW_ROOT, extracted_root=tmp_path)
    achievement_files = sorted((tmp_path / "quests").glob("Achievement_*.json"))
    assert achievement_files, "expected at least one achievement entity file"
    entity = json.loads(achievement_files[0].read_text(encoding="utf-8"))
    for key in ("id", "enabled", "display_name", "main_category", "description", "objective_ids"):
        assert key in entity, f"achievement entity missing key: {key}"


@pytest.mark.skipif(not QUEST_DIR.exists(), reason="raw data not present")
def test_leaderboard_entity_structure(tmp_path):
    """Spot-check: a leaderboard entity must have the required keys."""
    run(raw_root=RAW_ROOT, extracted_root=tmp_path)
    leaderboard_files = sorted((tmp_path / "quests").glob("Id_Leaderboard_*.json"))
    assert leaderboard_files, "expected at least one leaderboard entity file"
    entity = json.loads(leaderboard_files[0].read_text(encoding="utf-8"))
    for key in ("id", "season_name", "leaderboard_type"):
        assert key in entity, f"leaderboard entity missing key: {key}"


@pytest.mark.skipif(not QUEST_DIR.exists(), reason="raw data not present")
def test_announce_entity_structure(tmp_path):
    """Spot-check: an announce entity must have the required keys."""
    run(raw_root=RAW_ROOT, extracted_root=tmp_path)
    announce_files = sorted((tmp_path / "quests").glob("Id_Announce_*.json"))
    assert announce_files, "expected at least one announce entity file"
    entity = json.loads(announce_files[0].read_text(encoding="utf-8"))
    for key in ("id", "announce_text"):
        assert key in entity, f"announce entity missing key: {key}"


@pytest.mark.skipif(not QUEST_DIR.exists(), reason="raw data not present")
def test_triumph_level_entity_structure(tmp_path):
    """Spot-check: a triumph level entity must have the required keys."""
    run(raw_root=RAW_ROOT, extracted_root=tmp_path)
    tl_files = sorted((tmp_path / "quests").glob("Id_TriumphLevel_*.json"))
    assert tl_files, "expected at least one triumph level entity file"
    entity = json.loads(tl_files[0].read_text(encoding="utf-8"))
    assert "id" in entity, "triumph level entity missing key: id"
