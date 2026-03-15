"""Smoke test for monsters domain run() function."""
from pathlib import Path
from pipeline.domains.monsters import run


def test_monsters_run_smoke(tmp_path):
    """run() completes without error on empty raw dirs."""
    raw = tmp_path / "raw"
    raw.mkdir()
    extracted = tmp_path / "extracted"
    summary = run(raw_root=raw, extracted_root=extracted)
    assert isinstance(summary, dict)
    assert "monsters" in summary
    assert isinstance(summary["monsters"], int)
