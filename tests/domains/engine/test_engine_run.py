"""Smoke test for engine domain run() function."""
import json
from pathlib import Path
from pipeline.domains.engine import run


def test_engine_run_smoke(tmp_path):
    """run() completes without error even on empty raw dirs."""
    raw = tmp_path / "raw"
    raw.mkdir()
    extracted = tmp_path / "extracted"
    summary = run(raw_root=raw, extracted_root=extracted)
    assert (extracted / "engine" / "enums.json").exists()
    assert isinstance(summary, dict)
    required_keys = ("enums", "constants", "curve_tables", "curve_floats", "tag_dirs_scanned")
    assert all(k in summary for k in required_keys)
    assert all(isinstance(summary[k], int) for k in required_keys)
