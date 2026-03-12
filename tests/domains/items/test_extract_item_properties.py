"""Tests for pipeline/domains/items/extract_item_properties.py"""
import json
from pathlib import Path
from pipeline.domains.items.extract_item_properties import (
    extract_item_property_type,
    build_property_lookup,
    run_item_property_types,
)


def make_property_type_file(tmp_path, name, property_tag, value_ratio=1.0):
    data = [{
        "Type": "DCItemPropertyTypeDataAsset",
        "Name": name,
        "Properties": {
            "PropertyTypeGroupId": 40,
            "PropertyType": {"TagName": property_tag},
            "ValueRatio": value_ratio,
        }
    }]
    f = tmp_path / f"{name}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def make_item_property_file(tmp_path, name, item_suffix, entries):
    data = [{
        "Type": "DCItemPropertyDataAsset",
        "Name": name,
        "Properties": {
            "ItemPropertyItemArray": entries
        }
    }]
    f = tmp_path / f"{name}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_item_property_type_returns_id_and_tag(tmp_path):
    f = make_property_type_file(
        tmp_path, "Id_ItemPropertyType_Effect_ActionSpeed",
        "Type.Item.Property.Effect.ActionSpeed", value_ratio=0.001
    )
    result = extract_item_property_type(f)
    assert result is not None
    assert result["id"] == "Id_ItemPropertyType_Effect_ActionSpeed"
    assert result["property_type"] == "Type.Item.Property.Effect.ActionSpeed"
    assert result["value_ratio"] == 0.001


def test_extract_item_property_type_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "Other"}]', encoding="utf-8")
    assert extract_item_property_type(f) is None


def test_run_item_property_types_writes_system_file(tmp_path):
    type_dir = tmp_path / "types"
    type_dir.mkdir()
    make_property_type_file(type_dir, "Id_ItemPropertyType_Effect_MoveSpeed",
                            "Type.Item.Property.Effect.MoveSpeed", value_ratio=1.0)
    extracted = tmp_path / "extracted"
    result = run_item_property_types(type_dir=type_dir, extracted_root=extracted)
    out = extracted / "items" / "item_property_types.json"
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "types" in data
    assert "_meta" in data
    assert isinstance(data["_meta"]["source_files"], list)
    assert "Id_ItemPropertyType_Effect_MoveSpeed" in result


def test_build_property_lookup_returns_dict_keyed_by_item_id(tmp_path):
    prop_dir = tmp_path / "props"
    prop_dir.mkdir()
    make_item_property_file(
        prop_dir,
        "Id_ItemProperty_Primary_AdventurerBoots_1001",
        "AdventurerBoots_1001",
        [{"PropertyTypeId": {"TagName": "Type.Item.Property.ArmorRating"},
          "MinValue": 23, "MaxValue": 23, "EnchantMinValue": 0, "EnchantMaxValue": 0}]
    )
    lookup = build_property_lookup(prop_dir)
    assert "Id_Item_AdventurerBoots_1001" in lookup
    entries = lookup["Id_Item_AdventurerBoots_1001"]
    assert len(entries) == 1
    assert entries[0]["min_value"] == 23
    assert entries[0]["property_type"] == "Type.Item.Property.ArmorRating"
