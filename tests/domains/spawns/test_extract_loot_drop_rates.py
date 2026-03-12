"""Tests for pipeline/domains/spawns/extract_loot_drop_rates.py"""
import json
from pathlib import Path
from pipeline.domains.spawns.extract_loot_drop_rates import extract_loot_drop_rate, run_loot_drop_rates


def make_loot_drop_rate_file(tmp_path, rate_id):
    data = [{
        "Type": "DCLootDropRateDataAsset",
        "Name": rate_id,
        "Properties": {
            "LootDropRateItemArray": [
                {"LuckGrade": 1, "DropRate": 0.5},
                {"LuckGrade": 2, "DropRate": 0.3},
                {"LuckGrade": 3, "DropRate": 0.2},
            ]
        }
    }]
    f = tmp_path / f"{rate_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_loot_drop_rate_returns_id_and_rates(tmp_path):
    f = make_loot_drop_rate_file(tmp_path, "LDR_Common")
    result = extract_loot_drop_rate(f)
    assert result is not None
    assert result["id"] == "LDR_Common"
    assert isinstance(result["rates"], list)
    assert len(result["rates"]) == 3
    rate = result["rates"][0]
    assert rate["luck_grade"] == 1
    assert rate["drop_rate"] == 0.5


def test_extract_loot_drop_rate_handles_empty_rates(tmp_path):
    data = [{"Type": "DCLootDropRateDataAsset", "Name": "LDR_Empty",
             "Properties": {"LootDropRateItemArray": []}}]
    f = tmp_path / "empty.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    result = extract_loot_drop_rate(f)
    assert result is not None
    assert result["rates"] == []


def test_extract_loot_drop_rate_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_loot_drop_rate(f) is None


def test_run_loot_drop_rates_writes_entity_and_index(tmp_path):
    rates_dir = tmp_path / "rates"
    rates_dir.mkdir()
    make_loot_drop_rate_file(rates_dir, "LDR_Common")
    extracted = tmp_path / "extracted"
    result = run_loot_drop_rates(loot_drop_rate_dir=rates_dir, extracted_root=extracted)
    entity = extracted / "spawns" / "LDR_Common.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id"] == "LDR_Common"
    assert len(data["rates"]) == 3
    assert "_meta" in data
    index = extracted / "spawns" / "_index.json"
    assert index.exists()
    assert "LDR_Common" in result
