"""Tests for pipeline/domains/engine/extract_tags.py"""
import json
from pathlib import Path
from pipeline.domains.engine.extract_tags import run_tags


def make_tag_file(tmp_path, name, tag_type, tags):
    data = [{
        "Type": tag_type,
        "Name": name,
        "Properties": {"Tags": tags}
    }]
    f = tmp_path / f"{name}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_run_tags_writes_output(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    make_tag_file(raw_dir, "Id_TagGroup_Test", "IdTagGroup",
                  [{"TagName": "State.Test.Active"}])
    extracted = tmp_path / "extracted"
    run_tags(raw_dirs=[raw_dir], extracted_root=extracted)
    out = extracted / "engine" / "tags.json"
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "_meta" in data
    assert isinstance(data["_meta"]["source_files"], list)


def test_run_tags_groups_by_type(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    make_tag_file(raw_dir, "Id_TagGroup_Combat", "IdTagGroup",
                  [{"TagName": "State.Combat.Active"}])
    make_tag_file(raw_dir, "Id_CueGroup_Hit", "GameplayCueTagGroup",
                  [{"TagName": "GameplayCue.Hit"}])
    extracted = tmp_path / "extracted"
    run_tags(raw_dirs=[raw_dir], extracted_root=extracted)
    data = json.loads((extracted / "engine" / "tags.json").read_text(encoding="utf-8"))
    assert "id_tag_groups" in data
    assert "gameplay_cue_tag_groups" in data
    # Check actual extracted content
    id_groups = data["id_tag_groups"]
    assert len(id_groups) == 1
    assert id_groups[0]["name"] == "Id_TagGroup_Combat"
    assert "State.Combat.Active" in id_groups[0]["tags"]


def test_run_tags_skips_unknown_types(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    f = raw_dir / "unknown.json"
    f.write_text('[{"Type": "SomeUnknownType", "Name": "X", "Properties": {"Tags": []}}]',
                 encoding="utf-8")
    extracted = tmp_path / "extracted"
    run_tags(raw_dirs=[raw_dir], extracted_root=extracted)
    data = json.loads((extracted / "engine" / "tags.json").read_text(encoding="utf-8"))
    # All group lists should be empty
    assert all(len(v) == 0 for k, v in data.items() if not k.startswith("_"))
