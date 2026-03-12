"""Tests for pipeline/domains/dungeons/extract_floor_rules.py"""
import json
from pathlib import Path
from pipeline.domains.dungeons.extract_floor_rules import (
    extract_floor_portal, extract_floor_rule_blizzard, extract_floor_rule_deathswarm,
    run_floor_rules,
)


def make_file(tmp_path, subdir, filename, data):
    d = tmp_path / subdir
    d.mkdir(parents=True, exist_ok=True)
    f = d / filename
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_floor_portal_returns_fields(tmp_path):
    f = make_file(tmp_path, "FloorPortal", "Id_FloorPortal_A.json", [{
        "Type": "DCFloorPortalDataAsset",
        "Name": "Id_FloorPortal_A",
        "Properties": {"PortalType": "EPortalType::Normal", "PortalScrollNum": 2}
    }])
    result = extract_floor_portal(f)
    assert result is not None
    assert result["id"] == "Id_FloorPortal_A"
    assert result["portal_type"] == "EPortalType::Normal"
    assert result["portal_scroll_num"] == 2


def test_extract_floor_portal_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_floor_portal(f) is None


def test_extract_floor_rule_blizzard_returns_id(tmp_path):
    f = tmp_path / "blizzard.json"
    f.write_text('[{"Type": "DCFloorRuleBlizzardDataAsset", "Name": "Id_Blizzard_A"}]',
                 encoding="utf-8")
    result = extract_floor_rule_blizzard(f)
    assert result is not None
    assert result["id"] == "Id_Blizzard_A"


def test_extract_floor_rule_blizzard_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_floor_rule_blizzard(f) is None


def test_extract_floor_rule_deathswarm_returns_fields(tmp_path):
    data = [{"Type": "DCFloorRuleDeathSwarmDataAsset", "Name": "Id_DeathSwarm_A",
             "Properties": {"FloorRuleItemArray": [{"item": 1}]}}]
    f = tmp_path / "deathswarm.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    result = extract_floor_rule_deathswarm(f)
    assert result is not None
    assert result["id"] == "Id_DeathSwarm_A"
    assert result["floor_rule_items"] == [{"item": 1}]


def test_extract_floor_rule_deathswarm_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_floor_rule_deathswarm(f) is None


def test_run_floor_rules_writes_entities_and_combined_index(tmp_path):
    floor_rule_dir = tmp_path / "FloorRule"
    make_file(floor_rule_dir, "FloorPortal", "Id_FloorPortal_A.json", [{
        "Type": "DCFloorPortalDataAsset", "Name": "Id_FloorPortal_A",
        "Properties": {"PortalType": "EPortalType::Normal", "PortalScrollNum": 1}
    }])
    make_file(floor_rule_dir, "FloorRuleBlizzard", "Id_Blizzard_A.json", [
        {"Type": "DCFloorRuleBlizzardDataAsset", "Name": "Id_Blizzard_A"}
    ])
    make_file(floor_rule_dir, "FloorRuleDeathSwarm", "Id_DeathSwarm_A.json", [{
        "Type": "DCFloorRuleDeathSwarmDataAsset", "Name": "Id_DeathSwarm_A",
        "Properties": {"FloorRuleItemArray": []}
    }])
    extracted = tmp_path / "extracted"
    result = run_floor_rules(floor_rule_dir=floor_rule_dir, extracted_root=extracted)
    assert "Id_FloorPortal_A" in result
    assert "Id_Blizzard_A" in result
    assert "Id_DeathSwarm_A" in result
    assert result["Id_FloorPortal_A"]["_entity_type"] == "floor_portal"
    assert result["Id_Blizzard_A"]["_entity_type"] == "floor_rule_blizzard"
    assert result["Id_DeathSwarm_A"]["_entity_type"] == "floor_rule_deathswarm"
    portal_file = extracted / "dungeons" / "Id_FloorPortal_A.json"
    assert portal_file.exists()
