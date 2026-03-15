"""Smoke test for classes domain run() function."""
from pathlib import Path
from pipeline.domains.classes import run


def test_classes_run_smoke(tmp_path):
    """run() completes without error on empty raw dirs."""
    import json
    raw = tmp_path / "raw"
    raw.mkdir()
    extracted = tmp_path / "extracted"
    summary = run(raw_root=raw, extracted_root=extracted)
    assert isinstance(summary, dict)
    required_keys = ("player_characters", "perks", "skills", "shapeshifts")
    assert all(k in summary for k in required_keys)
    assert all(isinstance(summary[k], int) for k in required_keys)
    # Combined index is always written (may be empty if all dirs missing)
    index_path = extracted / "classes" / "_index.json"
    assert index_path.exists()
    data = json.loads(index_path.read_text(encoding="utf-8"))
    assert "count" in data
