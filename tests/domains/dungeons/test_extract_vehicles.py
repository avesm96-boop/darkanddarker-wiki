"""Tests for pipeline/domains/dungeons/extract_vehicles.py"""
import json
from pathlib import Path
from pipeline.domains.dungeons.extract_vehicles import (
    extract_vehicle, extract_vehicle_effect, extract_vehicle_interact,
    run_vehicles,
)


def make_file(tmp_path, subdir, filename, data):
    d = tmp_path / subdir
    d.mkdir(parents=True, exist_ok=True)
    f = d / filename
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_vehicle_returns_id_and_fields(tmp_path):
    f = make_file(tmp_path, "Vehicle", "Id_Vehicle_Boat.json", [{
        "Type": "DCVehicleDataAsset",
        "Name": "Id_Vehicle_Boat",
        "Properties": {
            "IdTag": {"TagName": "Vehicle.Boat"},
            "Name": {"LocalizedString": "Boat"},
            "SwimmingMovementModifier": {
                "AssetPathName": "/Game/.../MM_Swimming.MM_Swimming", "SubPathString": ""},
        }
    }])
    result = extract_vehicle(f)
    assert result is not None
    assert result["id"] == "Id_Vehicle_Boat"
    assert result["id_tag"] == "Vehicle.Boat"
    assert result["name"] == "Boat"
    assert result["swimming_movement_modifier"] == "MM_Swimming"


def test_extract_vehicle_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_vehicle(f) is None


def test_extract_vehicle_effect_returns_id_and_stats(tmp_path):
    data = [{
        "Type": "DCGameplayEffectDataAsset",
        "Name": "Id_VehicleEffect_Boat",
        "Properties": {
            "StrengthBase": 10,
            "VigorBase": 5,
            "AgilityBase": 8,
            "DexterityBase": 7,
            "WillBase": 6,
            "KnowledgeBase": 4,
            "ResourcefulnessBase": 3,
            "ImpactResistance": 20,
            "MoveSpeedBase": 150,
        }
    }]
    f = tmp_path / "effect.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    result = extract_vehicle_effect(f)
    assert result is not None
    assert result["id"] == "Id_VehicleEffect_Boat"
    assert result["strength_base"] == 10
    assert result["move_speed_base"] == 150


def test_extract_vehicle_effect_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_vehicle_effect(f) is None


def test_extract_vehicle_interact_returns_id_and_fields(tmp_path):
    data = [{
        "Type": "DCPropsInteractDataAsset",
        "Name": "Id_VehicleInteract_Boat",
        "Properties": {
            "InteractionName": {"LocalizedString": "Board Boat"},
            "InteractionText": {"LocalizedString": "Press F"},
            "Duration": 0.5,
            "InteractableTag": {"TagName": "Interact.Boat"},
            "TriggerTag": {"TagName": "Trigger.Board"},
            "AbilityTriggerTag": {"TagName": "Ability.Board"},
        }
    }]
    f = tmp_path / "interact.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    result = extract_vehicle_interact(f)
    assert result is not None
    assert result["id"] == "Id_VehicleInteract_Boat"
    assert result["interaction_name"] == "Board Boat"


def test_extract_vehicle_interact_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_vehicle_interact(f) is None


def test_run_vehicles_writes_entities_and_combined_index(tmp_path):
    vehicle_dir = tmp_path / "Vehicle"
    make_file(vehicle_dir, "Vehicle", "Id_Vehicle_Boat.json", [{
        "Type": "DCVehicleDataAsset", "Name": "Id_Vehicle_Boat",
        "Properties": {
            "IdTag": {"TagName": "Vehicle.Boat"},
            "Name": {"LocalizedString": "Boat"},
            "SwimmingMovementModifier": None,
        }
    }])
    make_file(vehicle_dir, "VehicleEffect", "Id_VehicleEffect_Boat.json", [{
        "Type": "DCGameplayEffectDataAsset", "Name": "Id_VehicleEffect_Boat",
        "Properties": {"StrengthBase": 10}
    }])
    make_file(vehicle_dir, "VehicleInteract", "Id_VehicleInteract_Boat.json", [{
        "Type": "DCPropsInteractDataAsset", "Name": "Id_VehicleInteract_Boat",
        "Properties": {
            "InteractionName": {"LocalizedString": "Board"},
            "InteractionText": {"LocalizedString": "Press F"},
            "Duration": 0.5,
            "InteractableTag": {"TagName": "Interact.Boat"},
            "TriggerTag": None, "AbilityTriggerTag": None,
        }
    }])
    extracted = tmp_path / "extracted"
    result = run_vehicles(vehicle_dir=vehicle_dir, extracted_root=extracted)
    assert "Id_Vehicle_Boat" in result
    assert "Id_VehicleEffect_Boat" in result
    assert "Id_VehicleInteract_Boat" in result
    assert result["Id_Vehicle_Boat"]["_entity_type"] == "vehicle"
    assert result["Id_VehicleEffect_Boat"]["_entity_type"] == "vehicle_effect"
    assert result["Id_VehicleInteract_Boat"]["_entity_type"] == "vehicle_interact"
    assert (extracted / "dungeons" / "Id_Vehicle_Boat.json").exists()
