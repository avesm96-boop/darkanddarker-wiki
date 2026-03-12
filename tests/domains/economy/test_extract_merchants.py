"""Tests for pipeline/domains/economy/extract_merchants.py"""
import json
from pathlib import Path
from pipeline.domains.economy.extract_merchants import extract_merchant, run_merchants


def make_merchant_file(tmp_path, merchant_id):
    data = [{"Type": "DCBaseGearDataAsset", "Name": merchant_id, "Properties": {
        "BaseGearItemArray": [{
            "UniqueID": 2,
            "ItemId": {"AssetPathName": "/Game/.../Id_Item_ArmingSword_1001.Id_Item_ArmingSword_1001", "SubPathString": ""},
            "MerchantId": {"AssetPathName": "/Game/.../Id_Merchant_Weaponsmith.Id_Merchant_Weaponsmith", "SubPathString": ""},
            "RequiredAffinity": 0,
        }]
    }}]
    f = tmp_path / f"{merchant_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_merchant_returns_id_and_items(tmp_path):
    f = make_merchant_file(tmp_path, "Id_BaseGear_Squire_Test")
    result = extract_merchant(f)
    assert result is not None
    assert result["id"] == "Id_BaseGear_Squire_Test"
    assert isinstance(result["items"], list)
    assert len(result["items"]) == 1
    item = result["items"][0]
    assert item["unique_id"] == 2
    assert item["item_id"] == "Id_Item_ArmingSword_1001"
    assert item["merchant_id"] == "Id_Merchant_Weaponsmith"
    assert item["required_affinity"] == 0


def test_extract_merchant_handles_empty_items(tmp_path):
    data = [{"Type": "DCBaseGearDataAsset", "Name": "Id_BaseGear_Empty", "Properties": {"BaseGearItemArray": []}}]
    f = tmp_path / "empty.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    result = extract_merchant(f)
    assert result is not None
    assert result["items"] == []


def test_extract_merchant_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_merchant(f) is None


def test_run_merchants_writes_entity_and_index(tmp_path):
    merchant_dir = tmp_path / "merchants"
    merchant_dir.mkdir()
    make_merchant_file(merchant_dir, "Id_BaseGear_Squire_Test")
    extracted = tmp_path / "extracted"
    result = run_merchants(merchant_dir=merchant_dir, extracted_root=extracted)
    entity = extracted / "economy" / "Id_BaseGear_Squire_Test.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id"] == "Id_BaseGear_Squire_Test"
    assert isinstance(data["items"], list)
    assert "_meta" in data
    index = extracted / "economy" / "_index.json"
    assert index.exists()
    assert "Id_BaseGear_Squire_Test" in result
