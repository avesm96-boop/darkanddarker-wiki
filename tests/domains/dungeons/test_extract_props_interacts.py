"""Tests for pipeline/domains/dungeons/extract_props_interacts.py"""
import json
from pathlib import Path
from pipeline.domains.dungeons.extract_props_interacts import extract_props_interact, run_props_interacts


def make_props_interact_file(tmp_path, interact_id):
    data = [{
        "Type": "DCPropsInteractDataAsset",
        "Name": interact_id,
        "Properties": {
            "InteractionName": {"LocalizedString": "Open Chest"},
            "InteractionText": {"LocalizedString": "Press F to open"},
            "Duration": 1.5,
            "InteractableTag": {"TagName": "Interact.Chest"},
            "TriggerTag": {"TagName": "Trigger.Open"},
            "AbilityTriggerTag": {"TagName": "Ability.OpenChest"},
        }
    }]
    f = tmp_path / f"{interact_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_props_interact_returns_id_and_fields(tmp_path):
    f = make_props_interact_file(tmp_path, "Id_PropsInteract_Chest")
    result = extract_props_interact(f)
    assert result is not None
    assert result["id"] == "Id_PropsInteract_Chest"
    assert result["interaction_name"] == "Open Chest"
    assert result["interaction_text"] == "Press F to open"
    assert result["duration"] == 1.5
    assert result["interactable_tag"] == "Interact.Chest"
    assert result["trigger_tag"] == "Trigger.Open"
    assert result["ability_trigger_tag"] == "Ability.OpenChest"


def test_extract_props_interact_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_props_interact(f) is None


def test_run_props_interacts_writes_entity_and_index(tmp_path):
    interacts_dir = tmp_path / "interacts"
    interacts_dir.mkdir()
    make_props_interact_file(interacts_dir, "Id_PropsInteract_Chest")
    extracted = tmp_path / "extracted"
    result = run_props_interacts(props_interact_dir=interacts_dir, extracted_root=extracted)
    entity = extracted / "dungeons" / "Id_PropsInteract_Chest.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["interaction_name"] == "Open Chest"
    assert "_meta" in data
    assert "Id_PropsInteract_Chest" in result
