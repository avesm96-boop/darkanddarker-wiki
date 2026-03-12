"""Tests for pipeline/domains/engine/extract_curves.py"""
import json
from pathlib import Path
from pipeline.domains.engine.extract_curves import extract_curve_table, run_curves


def make_curve_file(tmp_path, name, rows):
    data = [{
        "Type": "CurveTable",
        "Name": name,
        "CurveTableMode": "SimpleCurves",
        "Rows": rows
    }]
    f = tmp_path / f"{name}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_curve_table_returns_name_and_rows(tmp_path):
    rows = {
        "ActionSpeed": {
            "InterpMode": "RCIM_Linear",
            "Keys": [{"Time": 0, "Value": -0.38}, {"Time": 15, "Value": 0.0}]
        }
    }
    f = make_curve_file(tmp_path, "CT_ActionSpeed", rows)
    result = extract_curve_table(f)
    assert result["name"] == "CT_ActionSpeed"
    assert "ActionSpeed" in result["rows"]
    assert len(result["rows"]["ActionSpeed"]["keys"]) == 2


def test_extract_curve_table_returns_none_for_non_curve(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "Other"}]', encoding="utf-8")
    assert extract_curve_table(f) is None


def make_curve_float_file(tmp_path, name, keys):
    data = [{
        "Type": "CurveFloat",
        "Name": name,
        "Properties": {
            "FloatCurve": {
                "Keys": keys
            }
        }
    }]
    f = tmp_path / f"{name}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_run_curves_writes_system_file(tmp_path):
    raw_dir = tmp_path / "ga_dir"
    raw_dir.mkdir()
    make_curve_file(raw_dir, "CT_Agility", {
        "MoveSpeedBase": {"InterpMode": "RCIM_Linear", "Keys": [{"Time": 0, "Value": 0}]}
    })
    extracted = tmp_path / "extracted"
    run_curves(curve_dirs=[raw_dir], extracted_root=extracted)
    out = extracted / "engine" / "curves.json"
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "CT_Agility" in data["curve_tables"]


def test_extract_curve_float_returns_name_and_keys(tmp_path):
    f = make_curve_float_file(tmp_path, "CF_DamageFalloff",
                              [{"Time": 0.0, "Value": 1.0}, {"Time": 100.0, "Value": 0.5}])
    from pipeline.domains.engine.extract_curves import extract_curve_float
    result = extract_curve_float(f)
    assert result["name"] == "CF_DamageFalloff"
    assert len(result["keys"]) == 2


def test_extract_curve_float_returns_none_for_non_curve_float(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "Other"}]', encoding="utf-8")
    from pipeline.domains.engine.extract_curves import extract_curve_float
    assert extract_curve_float(f) is None


def test_run_curves_includes_curve_floats(tmp_path):
    raw_dir = tmp_path / "ga_dir"
    raw_dir.mkdir()
    make_curve_float_file(raw_dir, "CF_Test", [{"Time": 0.0, "Value": 1.0}])
    extracted = tmp_path / "extracted"
    run_curves(curve_dirs=[raw_dir], extracted_root=extracted)
    data = json.loads((extracted / "engine" / "curves.json").read_text(encoding="utf-8"))
    assert "CF_Test" in data["curve_floats"]
