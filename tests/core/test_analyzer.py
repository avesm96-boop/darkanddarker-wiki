"""Tests for pipeline/core/analyzer.py"""
from pipeline.core.analyzer import dps, drop_rate_pct, speed_at_base, add_notes, add_formula


def test_dps_calculation():
    assert abs(dps(40, 1.0) - 40.0) < 0.001
    assert abs(dps(40, 2.0) - 20.0) < 0.001


def test_dps_handles_zero_speed():
    assert dps(40, 0) == 0.0


def test_drop_rate_pct_calculation():
    result = drop_rate_pct(1, 4)
    assert abs(result - 25.0) < 0.001


def test_drop_rate_pct_handles_zero_total():
    assert drop_rate_pct(1, 0) == 0.0


def test_speed_at_base_applies_multiplier():
    assert abs(speed_at_base(0.65) - 195.0) < 0.001


def test_speed_at_base_custom_base():
    assert abs(speed_at_base(0.5, base=200) - 100.0) < 0.001


def test_add_notes_injects_list():
    data = {"id": "sword"}
    result = add_notes(data, ["note one", "note two"])
    assert result["_analysis_notes"] == ["note one", "note two"]


def test_add_notes_appends_to_existing():
    data = {"_analysis_notes": ["existing"]}
    result = add_notes(data, ["new note"])
    assert result["_analysis_notes"] == ["existing", "new note"]


def test_add_notes_returns_data():
    data = {"id": "x"}
    result = add_notes(data, ["n"])
    assert result is data


def test_add_formula_injects_formula():
    data = {"id": "x"}
    add_formula(data, "final_damage", "(base + bonus) * scale", "medium", ["caveat 1"])
    assert "_formulas" in data
    assert data["_formulas"][0]["name"] == "final_damage"
    assert data["_formulas"][0]["confidence"] == "medium"
    assert data["_formulas"][0]["caveats"] == ["caveat 1"]


def test_add_formula_appends_to_existing():
    data = {"_formulas": [{"name": "f1"}]}
    add_formula(data, "f2", "expr", "confirmed", [])
    assert len(data["_formulas"]) == 2
