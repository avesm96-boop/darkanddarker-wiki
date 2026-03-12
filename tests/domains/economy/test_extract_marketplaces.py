"""Tests for pipeline/domains/economy/extract_marketplaces.py"""
import json
from pathlib import Path
from pipeline.domains.economy.extract_marketplaces import extract_marketplace, run_marketplaces


def make_marketplace_file(tmp_path, marketplace_id):
    data = [{"Type": "DCMarketplaceDataAsset", "Name": marketplace_id, "Properties": {
        "Name": {"Namespace": "DC", "Key": "some_key", "LocalizedString": "Marketplace"},
        "Order": 1,
        "BasePayments": [{"AssetPathName": "/Game/.../Id_MarketplacePayment_GoldCoin.Id_MarketplacePayment_GoldCoin", "SubPathString": ""}],
    }}]
    f = tmp_path / f"{marketplace_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_marketplace_returns_id_and_fields(tmp_path):
    f = make_marketplace_file(tmp_path, "Id_Marketplace_GoldCoin")
    result = extract_marketplace(f)
    assert result is not None
    assert result["id"] == "Id_Marketplace_GoldCoin"
    assert result["name"] == "Marketplace"
    assert result["order"] == 1
    assert isinstance(result["base_payments"], list)
    assert len(result["base_payments"]) == 1
    assert result["base_payments"][0] == "Id_MarketplacePayment_GoldCoin"


def test_extract_marketplace_handles_empty_payments(tmp_path):
    data = [{"Type": "DCMarketplaceDataAsset", "Name": "Id_Marketplace_Empty",
             "Properties": {"Name": {"LocalizedString": "Empty Market"}, "Order": 0, "BasePayments": []}}]
    f = tmp_path / "empty.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    result = extract_marketplace(f)
    assert result is not None
    assert result["base_payments"] == []


def test_extract_marketplace_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_marketplace(f) is None


def test_run_marketplaces_writes_entity_and_index(tmp_path):
    marketplace_dir = tmp_path / "marketplaces"
    marketplace_dir.mkdir()
    make_marketplace_file(marketplace_dir, "Id_Marketplace_GoldCoin")
    extracted = tmp_path / "extracted"
    result = run_marketplaces(marketplace_dir=marketplace_dir, extracted_root=extracted)
    entity = extracted / "economy" / "Id_Marketplace_GoldCoin.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id"] == "Id_Marketplace_GoldCoin"
    assert data["name"] == "Marketplace"
    assert "_meta" in data
    index = extracted / "economy" / "_index.json"
    assert index.exists()
    assert "Id_Marketplace_GoldCoin" in result
