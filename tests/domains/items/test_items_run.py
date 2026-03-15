"""Smoke test for items domain run() function."""
import json
from pathlib import Path
from pipeline.domains.items import run


def test_items_run_smoke(tmp_path):
    """run() completes without error on empty raw dirs."""
    raw = tmp_path / "raw"
    raw.mkdir()
    extracted = tmp_path / "extracted"
    summary = run(raw_root=raw, extracted_root=extracted)
    assert isinstance(summary, dict)
    required_keys = ("items", "items_with_properties", "item_property_types")
    assert all(k in summary for k in required_keys)
    assert all(isinstance(summary[k], int) for k in required_keys)
