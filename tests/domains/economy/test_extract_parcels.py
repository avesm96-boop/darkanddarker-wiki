"""Tests for pipeline/domains/economy/extract_parcels.py"""
import json
from pathlib import Path
from pipeline.domains.economy.extract_parcels import extract_parcel, run_parcels


def make_parcel_file(tmp_path, parcel_id):
    data = [{"Type": "DCParcelDataAsset", "Name": parcel_id, "Properties": {
        "Name": {"LocalizedString": "Recovered Seasonal Pack Gold Coin Bag"},
        "FlavorText": {"LocalizedString": "A Parcel ready to be collected from the Expressman."},
        "ArtData": {"AssetPathName": "/Game/.../Reward_Parcel_CoinBagRestore_01.Reward_Parcel_CoinBagRestore_01", "SubPathString": ""},
        "ParcelRewards": [{"AssetPathName": "/Game/.../Id_Reward_Parcel_Restore_Bag_01.Id_Reward_Parcel_Restore_Bag_01", "SubPathString": ""}],
    }}]
    f = tmp_path / f"{parcel_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_parcel_returns_id_and_fields(tmp_path):
    f = make_parcel_file(tmp_path, "Id_Parcel_CoinBag_Restore_01")
    result = extract_parcel(f)
    assert result is not None
    assert result["id"] == "Id_Parcel_CoinBag_Restore_01"
    assert result["name"] == "Recovered Seasonal Pack Gold Coin Bag"
    assert result["flavor_text"] == "A Parcel ready to be collected from the Expressman."
    assert isinstance(result["parcel_rewards"], list)
    assert len(result["parcel_rewards"]) == 1
    assert result["parcel_rewards"][0] == "Id_Reward_Parcel_Restore_Bag_01"


def test_extract_parcel_handles_empty_rewards(tmp_path):
    data = [{"Type": "DCParcelDataAsset", "Name": "Id_Parcel_Empty",
             "Properties": {"Name": {"LocalizedString": "Empty Parcel"}, "FlavorText": {"LocalizedString": "Nothing here."}, "ParcelRewards": []}}]
    f = tmp_path / "empty.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    result = extract_parcel(f)
    assert result is not None
    assert result["parcel_rewards"] == []


def test_extract_parcel_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_parcel(f) is None


def test_run_parcels_writes_entity_and_index(tmp_path):
    parcel_dir = tmp_path / "parcels"
    parcel_dir.mkdir()
    make_parcel_file(parcel_dir, "Id_Parcel_CoinBag_Restore_01")
    extracted = tmp_path / "extracted"
    result = run_parcels(parcel_dir=parcel_dir, extracted_root=extracted)
    entity = extracted / "economy" / "Id_Parcel_CoinBag_Restore_01.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id"] == "Id_Parcel_CoinBag_Restore_01"
    assert data["name"] == "Recovered Seasonal Pack Gold Coin Bag"
    assert "_meta" in data
    index = extracted / "economy" / "_index.json"
    assert index.exists()
    assert "Id_Parcel_CoinBag_Restore_01" in result
