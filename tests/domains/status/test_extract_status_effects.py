"""Tests for pipeline/domains/status/extract_status_effects.py"""
import json
from pathlib import Path
from pipeline.domains.status.extract_status_effects import (
    extract_status_effect, run_status_effects
)


def make_status_file(tmp_path, status_id, extra_props=None):
    props = {
        "EventTag": {"TagName": "Event.Attack.Hit"},
        "AssetTags": [{"TagName": "State.ActorStatus.Buff.Haste"}],
        "Duration": 6000,
    }
    if extra_props:
        props.update(extra_props)
    data = [{
        "Type": "DCGameplayEffectDataAsset",
        "Name": status_id,
        "Properties": props,
    }]
    f = tmp_path / f"{status_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_status_effect_player_returns_id_and_fields(tmp_path):
    f = make_status_file(tmp_path, "Id_ActorStatusEffect_Haste")
    result = extract_status_effect(f, category="player")
    assert result is not None
    assert result["id"] == "Id_ActorStatusEffect_Haste"
    assert result["category"] == "player"
    assert result["event_tag"] == "Event.Attack.Hit"
    assert "State.ActorStatus.Buff.Haste" in result["asset_tags"]
    assert result["duration"] == 6000


def test_extract_status_effect_monster_with_target_type(tmp_path):
    f = make_status_file(
        tmp_path, "Id_ActorStatusEffect_Monster_Bite",
        extra_props={"TargetType": {"TagName": "Type.Target.Enemy"}}
    )
    result = extract_status_effect(f, category="monster")
    assert result is not None
    assert result["category"] == "monster"
    assert result["target_type"] == "Type.Target.Enemy"


def test_extract_status_effect_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "Other"}]', encoding="utf-8")
    assert extract_status_effect(f, category="player") is None


def test_run_status_effects_writes_entity_and_index(tmp_path):
    status_dir = tmp_path / "status"
    status_dir.mkdir()
    make_status_file(status_dir, "Id_ActorStatusEffect_Haste")
    extracted = tmp_path / "extracted"
    result = run_status_effects(
        status_dir=status_dir, category="player", extracted_root=extracted
    )
    entity = extracted / "status" / "Id_ActorStatusEffect_Haste.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["category"] == "player"
    assert data["event_tag"] == "Event.Attack.Hit"
    assert "_meta" in data
    index = extracted / "status" / "_index.json"
    assert index.exists()
    assert "Id_ActorStatusEffect_Haste" in result
