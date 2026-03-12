"""Tests for pipeline/domains/quests/extract_announces.py"""
import json
from pathlib import Path
from pipeline.domains.quests.extract_announces import extract_announce, run_announces


def make_announce_file(tmp_path, announce_id, text="The server will be down for maintenance in {0} minutes."):
    data = [{"Type": "DCAnnounceDataAsset", "Name": announce_id,
             "Properties": {"AnnounceText": {"Namespace": "DC", "LocalizedString": text}}}]
    f = tmp_path / f"{announce_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_announce_returns_id_and_fields(tmp_path):
    f = make_announce_file(tmp_path, "Id_Announce_AllMaintenaceAnnounce")
    result = extract_announce(f)
    assert result is not None
    assert result["id"] == "Id_Announce_AllMaintenaceAnnounce"
    assert result["announce_text"] == "The server will be down for maintenance in {0} minutes."


def test_extract_announce_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_announce(f) is None


def test_run_announces_writes_entity_and_index(tmp_path):
    announce_dir = tmp_path / "announces"
    announce_dir.mkdir()
    make_announce_file(announce_dir, "Id_Announce_AllMaintenaceAnnounce")
    make_announce_file(announce_dir, "Id_Announce_UpdateAnnounce", text="New patch available.")
    extracted = tmp_path / "extracted"
    result = run_announces(announce_dir=announce_dir, extracted_root=extracted)
    entity = extracted / "quests" / "Id_Announce_AllMaintenaceAnnounce.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id"] == "Id_Announce_AllMaintenaceAnnounce"
    assert "maintenance" in data["announce_text"]
    assert "_meta" in data
    index = extracted / "quests" / "_index.json"
    assert index.exists()
    assert "Id_Announce_AllMaintenaceAnnounce" in result
    assert "Id_Announce_UpdateAnnounce" in result
