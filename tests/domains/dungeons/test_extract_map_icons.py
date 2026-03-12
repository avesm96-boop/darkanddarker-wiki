"""Tests for pipeline/domains/dungeons/extract_map_icons.py"""
import json
from pathlib import Path
from pipeline.domains.dungeons.extract_map_icons import extract_map_icon, run_map_icons


def make_map_icon_file(tmp_path, icon_id):
    data = [{"Type": "DCMapIconDataAsset", "Name": icon_id}]
    f = tmp_path / f"{icon_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_map_icon_returns_id(tmp_path):
    f = make_map_icon_file(tmp_path, "Id_MapIcon_Portal")
    result = extract_map_icon(f)
    assert result is not None
    assert result["id"] == "Id_MapIcon_Portal"


def test_extract_map_icon_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_map_icon(f) is None


def test_run_map_icons_writes_entity_and_index(tmp_path):
    icons_dir = tmp_path / "icons"
    icons_dir.mkdir()
    make_map_icon_file(icons_dir, "Id_MapIcon_Portal")
    extracted = tmp_path / "extracted"
    result = run_map_icons(map_icon_dir=icons_dir, extracted_root=extracted)
    entity = extracted / "dungeons" / "Id_MapIcon_Portal.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id"] == "Id_MapIcon_Portal"
    assert "_meta" in data
    assert "Id_MapIcon_Portal" in result
