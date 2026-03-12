"""Tests for pipeline/domains/engine/extract_constants.py"""
import json
import pytest
from pathlib import Path
from pipeline.domains.engine.extract_constants import extract_constant, run_constants


def make_constant_file(tmp_path, const_name, value):
    data = [{
        "Type": "DCConstantDataAsset",
        "Name": const_name,
        "Properties": {
            "Item": {
                "ConstantId": {
                    "ObjectName": f"{const_name}'...'",
                    "ObjectPath": f"/Game/Data/{const_name}.0"
                },
                "ConstantValue": value
            }
        }
    }]
    f = tmp_path / f"{const_name}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_constant_returns_id_and_value(tmp_path):
    f = make_constant_file(tmp_path, "Id_Constant_CharacterBaseMoveSpeed", 300.0)
    result = extract_constant(f)
    assert result is not None
    assert result["id"] == "Id_Constant_CharacterBaseMoveSpeed"
    assert result["value"] == 300.0


def test_extract_constant_returns_none_for_non_constant(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "Other"}]', encoding="utf-8")
    assert extract_constant(f) is None


def test_run_constants_writes_system_file(tmp_path):
    raw_dir = tmp_path / "raw" / "V2" / "Constant" / "Constant"
    raw_dir.mkdir(parents=True)
    make_constant_file(raw_dir, "Id_Constant_MaxMoveSpeed", 330.0)
    extracted = tmp_path / "extracted"
    run_constants(raw_dir=raw_dir, extracted_root=extracted)
    out = extracted / "engine" / "constants.json"
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "constants" in data
    assert "_meta" in data
    assert isinstance(data["_meta"]["source_files"], list)
