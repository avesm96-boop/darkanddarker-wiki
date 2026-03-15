"""Tests for pipeline/domains/items/extract_items.py"""
import json
from pathlib import Path
from pipeline.domains.items.extract_items import extract_item, run_items


def make_item_file(tmp_path, item_id, name_str="Test Item", item_type="EItemType::Armor"):
    data = [{
        "Type": "DCItemDataAsset",
        "Name": item_id,
        "Properties": {
            "Name": {"Namespace": "DC", "Key": "k", "LocalizedString": name_str},
            "FlavorText": {"Namespace": "DC", "Key": "f", "LocalizedString": "Flavor text"},
            "ItemType": item_type,
            "SlotType": {"TagName": "Type.Item.Slot.Foot"},
            "RarityType": {"TagName": "Type.Item.Rarity.Common"},
            "MaxCount": 1,
            "CanDrop": True,
            "InventoryWidth": 2,
            "InventoryHeight": 2,
        }
    }]
    f = tmp_path / f"{item_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_item_returns_id_and_name(tmp_path):
    f = make_item_file(tmp_path, "Id_Item_AdventurerBoots_1001", "Adventurer Boots")
    result = extract_item(f)
    assert result is not None
    assert result["id"] == "Id_Item_AdventurerBoots_1001"
    assert result["name"] == "Adventurer Boots"
    assert result["item_type"] == "Armor"
    assert result["slot_type"] == "Type.Item.Slot.Foot"


def test_extract_item_merges_properties_from_lookup(tmp_path):
    f = make_item_file(tmp_path, "Id_Item_AdventurerBoots_1001")
    prop_entry = {"property_type": "Type.Item.Property.ArmorRating",
                  "min_value": 23, "max_value": 23,
                  "enchant_min_value": 0, "enchant_max_value": 0}
    lookup = {"Id_Item_AdventurerBoots_1001": [prop_entry]}
    result = extract_item(f, property_lookup=lookup)
    assert "properties" in result
    assert len(result["properties"]) == 1
    assert result["properties"][0]["min_value"] == 23


def test_extract_item_returns_none_for_non_item(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "Other"}]', encoding="utf-8")
    assert extract_item(f) is None


def test_run_items_writes_entity_files_and_index(tmp_path):
    item_dir = tmp_path / "items"
    item_dir.mkdir()
    make_item_file(item_dir, "Id_Item_TestSword_1001", "Test Sword", "EItemType::Weapon")
    extracted = tmp_path / "extracted"
    result = run_items(item_dir=item_dir, extracted_root=extracted)
    # entity file
    entity = extracted / "items" / "Id_Item_TestSword_1001.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["name"] == "Test Sword"
    assert "_meta" in data
    # index
    index = extracted / "items" / "_index.json"
    assert index.exists()
    assert "Id_Item_TestSword_1001" in result
