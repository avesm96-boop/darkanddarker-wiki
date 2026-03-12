"""Tests for pipeline/core/normalizer.py"""
from pipeline.core.normalizer import (
    flatten, resolve_ref, resolve_tag, resolve_text,
    camel_to_snake, clean_flags
)


def test_flatten_scalar_passthrough():
    assert flatten(42) == 42
    assert flatten("hello") == "hello"
    assert flatten(True) is True
    assert flatten(None) is None


def test_flatten_list_recurses():
    result = flatten([1, {"TagName": "A.B"}, 3])
    assert result[0] == 1
    assert result[1] == "A.B"
    assert result[2] == 3


def test_flatten_ue5_ref_resolves():
    val = {"ObjectName": "Id_Item_Sword'...'", "ObjectPath": "/Game/Data/Id.0"}
    result = flatten(val)
    assert result == "Id_Item_Sword"


def test_flatten_ue5_tag_resolves():
    val = {"TagName": "State.ActorStatus.Buff.Haste"}
    result = flatten(val)
    assert result == "State.ActorStatus.Buff.Haste"


def test_flatten_localized_string_resolves():
    val = {"LocalizedString": "Longsword"}
    result = flatten(val)
    assert result == "Longsword"


def test_flatten_nested_struct_snake_cases_keys():
    val = {"MoveSpeedBase": 300, "MaxMoveSpeed": 330}
    result = flatten(val)
    assert "move_speed_base" in result
    assert result["move_speed_base"] == 300


def test_resolve_ref_extracts_asset_name():
    val = {"ObjectName": "Id_Item_Sword'extra'", "ObjectPath": "/Game/Data.0"}
    assert resolve_ref(val) == "Id_Item_Sword"


def test_resolve_ref_returns_none_for_non_ref():
    assert resolve_ref({"Foo": "bar"}) is None


def test_resolve_tag_extracts_tag_name():
    assert resolve_tag({"TagName": "X.Y.Z"}) == "X.Y.Z"


def test_resolve_tag_returns_none_for_non_tag():
    assert resolve_tag({"Foo": "bar"}) is None


def test_resolve_text_extracts_string():
    assert resolve_text({"LocalizedString": "Hello"}) == "Hello"


def test_resolve_text_returns_none_for_non_text():
    assert resolve_text({"Foo": "bar"}) is None


def test_camel_to_snake_converts_pascal():
    assert camel_to_snake("MoveSpeedBase") == "move_speed_base"
    assert camel_to_snake("MaxMoveSpeed") == "max_move_speed"


def test_camel_to_snake_handles_acronyms():
    assert camel_to_snake("HPMax") == "h_p_max"


def test_clean_flags_strips_rf_prefix():
    flags = "RF_Public | RF_Standalone | RF_Transactional"
    result = clean_flags(flags)
    assert result == ["Public", "Standalone", "Transactional"]


def test_clean_flags_handles_empty():
    assert clean_flags("") == []
    assert clean_flags(None) == []
