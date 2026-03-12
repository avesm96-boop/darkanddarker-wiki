# Phase 4: Dungeons & Spawns Extraction Pipeline Design

## 1. Goal

Extract all dungeon and spawn data assets from the UE5 FModel JSON exports into the
standardised `extracted/` format used by all prior phases.

---

## 2. Scope

Two independent domain packages executed in parallel.

### 2.1 Dungeons domain

| V2 directory | Type | Files |
|---|---|---|
| `Dungeon/Dungeon/` | `DCDungeonDataAsset` | 143 |
| `Dungeon/DungeonType/` | `DCDungeonTypeDataAsset` | 21 |
| `Dungeon/DungeonGrade/` | `DCDungeonGradeDataAsset` | 62 |
| `Dungeon/DungeonCard/` | `DCDungeonCardDataAsset` | 14 |
| `Dungeon/DungeonLayout/` | `DCDungeonLayoutDataAsset` | 258 |
| `Dungeon/DungeonModule/` | `DCDungeonModuleDataAsset` | 283 |
| `FloorRule/FloorPortal/` | `DCFloorPortalDataAsset` | 5 |
| `FloorRule/FloorRuleBlizzard/` | `DCFloorRuleBlizzardDataAsset` | 73 |
| `FloorRule/FloorRuleDeathSwarm/` | `DCFloorRuleDeathSwarmDataAsset` | 30 |
| `Props/Props/` | `DCPropsDataAsset` | 952 |
| `Props/PropsEffect/` | `DCGameplayEffectDataAsset` | 153 |
| `Props/PropsInteract/` | `DCPropsInteractDataAsset` | 101 |
| `Props/PropsSkillCheck/` | `DCPropsSkillCheckDataAsset` | 5 |
| `MapIcon/MapIcon/` | `DCMapIconDataAsset` | 18 |
| `Vehicle/Vehicle/` | `DCVehicleDataAsset` | 8 |
| `Vehicle/VehicleEffect/` | `DCGameplayEffectDataAsset` | 4 |
| `Vehicle/VehicleInteract/` | `DCPropsInteractDataAsset` | 1 |

**Skipped:** `Props/PropsAbility/` and `Vehicle/VehicleAbility/` — both contain
`DCGameplayAbilityDataAsset`, skipped by the same type-filter pattern used in
Projectile, Aoe, and other mixed-type directories.

### 2.2 Spawns domain

| V2 directory | Type | Files |
|---|---|---|
| `Spawner/Spawner/` | `DCSpawnerDataAsset` | 501 |
| `LootDrop/LootDrop/` | `DCLootDropDataAsset` | 3,048 |
| `LootDrop/LootDropGroup/` | `DCLootDropGroupDataAsset` | 376 |
| `LootDrop/LootDropRate/` | `DCLootDropRateDataAsset` | 2,294 |

---

## 3. File Structure

```
pipeline/domains/dungeons/
    __init__.py                  ← orchestrator; combined-index
    extract_dungeons.py          ← DCDungeonDataAsset
    extract_dungeon_types.py     ← DCDungeonTypeDataAsset
    extract_dungeon_grades.py    ← DCDungeonGradeDataAsset
    extract_dungeon_cards.py     ← DCDungeonCardDataAsset
    extract_dungeon_layouts.py   ← DCDungeonLayoutDataAsset
    extract_dungeon_modules.py   ← DCDungeonModuleDataAsset
    extract_floor_rules.py       ← DCFloorPortalDataAsset + DCFloorRuleBlizzardDataAsset
                                    + DCFloorRuleDeathSwarmDataAsset (one file, three functions)
    extract_props.py             ← DCPropsDataAsset
    extract_props_effects.py     ← DCGameplayEffectDataAsset (Props/PropsEffect/)
    extract_props_interacts.py   ← DCPropsInteractDataAsset (Props/PropsInteract/)
    extract_props_skill_checks.py← DCPropsSkillCheckDataAsset
    extract_map_icons.py         ← DCMapIconDataAsset
    extract_vehicles.py          ← DCVehicleDataAsset + DCGameplayEffectDataAsset (VehicleEffect/)
                                    + DCPropsInteractDataAsset (VehicleInteract/)
                                    (one file, three functions, one run_vehicles())

pipeline/domains/spawns/
    __init__.py                  ← orchestrator; combined-index
    extract_spawners.py          ← DCSpawnerDataAsset
    extract_loot_drops.py        ← DCLootDropDataAsset
    extract_loot_drop_groups.py  ← DCLootDropGroupDataAsset
    extract_loot_drop_rates.py   ← DCLootDropRateDataAsset

tests/domains/dungeons/
    test_extract_dungeons.py
    test_extract_dungeon_types.py
    test_extract_dungeon_grades.py
    test_extract_dungeon_cards.py
    test_extract_dungeon_layouts.py
    test_extract_dungeon_modules.py
    test_extract_floor_rules.py
    test_extract_props.py
    test_extract_props_effects.py
    test_extract_props_interacts.py
    test_extract_props_skill_checks.py
    test_extract_map_icons.py
    test_extract_vehicles.py
    test_dungeons_integration.py

tests/domains/spawns/
    test_extract_spawners.py
    test_extract_loot_drops.py
    test_extract_loot_drop_groups.py
    test_extract_loot_drop_rates.py
    test_spawns_integration.py
```

---

## 4. Fields Extracted

### 4.1 Dungeons

#### `extract_dungeons.py` — `DCDungeonDataAsset`
```python
{
    "id": obj["Name"],
    "id_tag": resolve_tag(props["IdTag"]),
    "name": resolve_text(props["Name"]),
    "game_types": props.get("GameTypes") or [],        # list of "EGameType::Xxx" strings
    "default_dungeon_grade": props.get("DefaultDungeonGrade"),  # plain integer, not AssetPathName
    "floor": props.get("floor"),
    "floor_rule": _extract_asset_id(props.get("FloorRule")),  # AssetPathName ref
    "triumph_exp": props.get("TriumphExp"),
    "module_type": props.get("ModuleType"),            # "EDCDungeonModuleType::Xxx"
    "fog_enabled": props.get("bFogEnabled"),
    "num_min_escapes": props.get("NumMinEscapes"),
}
```

#### `extract_dungeon_types.py` — `DCDungeonTypeDataAsset`
```python
{
    "id": obj["Name"],
    "id_tag": resolve_tag(props["IdTag"]),
    "name": resolve_text(props["Name"]),
    "group_name": resolve_text(props.get("GroupName")),
    "chapter_name": resolve_text(props.get("ChapterName")),
    "desc": resolve_text(props.get("Desc")),
    "order": props.get("Order"),
}
```

#### `extract_dungeon_grades.py` — `DCDungeonGradeDataAsset`

NOTE: The field is named `DungeonIdTag` (not `IdTag`). `.get()` is used intentionally
— some grade records may omit this field.

```python
{
    "id": obj["Name"],
    "dungeon_id_tag": resolve_tag(props.get("DungeonIdTag")),
    "gear_pool_index": props.get("GearPoolIndex"),
}
```

#### `extract_dungeon_cards.py` — `DCDungeonCardDataAsset`
```python
{
    "id": obj["Name"],    # no Properties in source data
}
```

#### `extract_dungeon_layouts.py` — `DCDungeonLayoutDataAsset`
```python
{
    "id": obj["Name"],
    "size_x": (props.get("Size") or {}).get("X"),
    "size_y": (props.get("Size") or {}).get("Y"),
}
```

#### `extract_dungeon_modules.py` — `DCDungeonModuleDataAsset`
```python
{
    "id": obj["Name"],
    "name": resolve_text(props.get("Name")),
    "module_type": props.get("ModuleType"),
    "size_x": (props.get("Size") or {}).get("X"),
    "size_y": (props.get("Size") or {}).get("Y"),
}
```

#### `extract_floor_rules.py` — three functions, one `run_floor_rules()`

**`extract_floor_portal`** — `DCFloorPortalDataAsset`:
```python
{
    "id": obj["Name"],
    "portal_type": props.get("PortalType"),
    "portal_scroll_num": props.get("PortalScrollNum"),
}
```

**`extract_floor_rule_blizzard`** — `DCFloorRuleBlizzardDataAsset`:
```python
{
    "id": obj["Name"],    # minimal/no properties in source data
}
```

**`extract_floor_rule_deathswarm`** — `DCFloorRuleDeathSwarmDataAsset`:
```python
{
    "id": obj["Name"],
    "floor_rule_items": props.get("FloorRuleItemArray") or [],  # stored raw
}
```

`run_floor_rules(floor_rule_dir, extracted_root)` scans all three sub-directories,
tags each entity with `_entity_type` of `floor_portal`, `floor_rule_blizzard`, or
`floor_rule_deathswarm`, and returns a combined `{id: entity}` dict.

#### `extract_props.py` — `DCPropsDataAsset`
```python
{
    "id": obj["Name"],
    "id_tag": resolve_tag(props.get("IdTag")),
    "name": resolve_text(props.get("Name")),
    "grade_type": resolve_tag(props.get("GradeType")),
    "adv_point": props.get("AdvPoint"),
    "exp_point": props.get("ExpPoint"),
}
```

#### `extract_props_effects.py` — `DCGameplayEffectDataAsset` (Props/PropsEffect/)

NOTE: Same UE5 type as the status domain, but `Props/PropsEffect/` source files only
carry `EffectClass`, `EventTag`, and `AssetTags`. `Duration` and `TargetType` are
absent in this sub-directory and intentionally not extracted here.

```python
{
    "id": obj["Name"],
    "event_tag": resolve_tag(props.get("EventTag")),
    "asset_tags": [resolve_tag(t) for t in (props.get("AssetTags") or [])
                   if resolve_tag(t) is not None],
}
```

#### `extract_props_interacts.py` — `DCPropsInteractDataAsset`
```python
{
    "id": obj["Name"],
    "interaction_name": resolve_text(props.get("InteractionName")),
    "interaction_text": resolve_text(props.get("InteractionText")),
    "duration": props.get("Duration"),
    "interactable_tag": resolve_tag(props.get("InteractableTag")),
    "trigger_tag": resolve_tag(props.get("TriggerTag")),
    "ability_trigger_tag": resolve_tag(props.get("AbilityTriggerTag")),
}
```

#### `extract_props_skill_checks.py` — `DCPropsSkillCheckDataAsset`
```python
{
    "id": obj["Name"],
    "skill_check_type": props.get("SkillCheckType"),
    "min_duration": props.get("MinDuration"),
    "max_duration": props.get("MaxDuration"),
    "min_skill_check_interval": props.get("MinSkillCheckInterval"),
    "max_skill_check_interval": props.get("MaxSkillCheckInterval"),
}
```

#### `extract_map_icons.py` — `DCMapIconDataAsset`
```python
{
    "id": obj["Name"],    # no Properties in source data
}
```

#### `extract_vehicles.py` — three functions, one `run_vehicles()`

**`extract_vehicle`** — `DCVehicleDataAsset`:
```python
{
    "id": obj["Name"],
    "id_tag": resolve_tag(props.get("IdTag")),
    "name": resolve_text(props.get("Name")),
    "swimming_movement_modifier": _extract_asset_id(props.get("SwimmingMovementModifier")),  # AssetPathName ref
}
```

**`extract_vehicle_effect`** — `DCGameplayEffectDataAsset` (Vehicle/VehicleEffect/):
```python
{
    "id": obj["Name"],
    "strength_base": props.get("StrengthBase"),
    "vigor_base": props.get("VigorBase"),
    "agility_base": props.get("AgilityBase"),
    "dexterity_base": props.get("DexterityBase"),
    "will_base": props.get("WillBase"),
    "knowledge_base": props.get("KnowledgeBase"),
    "resourcefulness_base": props.get("ResourcefulnessBase"),
    "impact_resistance": props.get("ImpactResistance"),
    "move_speed_base": props.get("MoveSpeedBase"),
}
```

**`extract_vehicle_interact`** — `DCPropsInteractDataAsset` (Vehicle/VehicleInteract/):
Same fields as `extract_props_interacts.py`.

`run_vehicles(vehicle_dir, extracted_root)` scans `Vehicle/`, `VehicleEffect/`, and
`VehicleInteract/` sub-directories, skipping `VehicleAbility/`. Tags entities with
`_entity_type` of `vehicle`, `vehicle_effect`, or `vehicle_interact`.

---

### 4.2 Spawns

#### `extract_spawners.py` — `DCSpawnerDataAsset`
```python
{
    "id": obj["Name"],
    "spawner_items": [
        {
            "spawn_rate": item.get("SpawnRate"),
            "dungeon_grades": item.get("DungeonGrades") or [],
            "loot_drop_group_id": _extract_asset_id(item.get("LootDropGroupId")),
            "monster_id": _extract_asset_id(item.get("MonsterId")),
            "props_id": _extract_asset_id(item.get("PropsId")),
        }
        for item in (props.get("SpawnerItemArray") or [])
    ],
}
```

Uses the same `_extract_asset_id()` helper pattern as `extract_aoes.py` for
`{AssetPathName, SubPathString}` references.

#### `extract_loot_drops.py` — `DCLootDropDataAsset`
```python
{
    "id": obj["Name"],
    "items": [
        {
            "item_id": _extract_asset_id(item.get("ItemId")),
            "item_count": item.get("ItemCount"),
            "luck_grade": item.get("LuckGrade"),
        }
        for item in (props.get("LootDropItemArray") or [])
    ],
}
```

#### `extract_loot_drop_groups.py` — `DCLootDropGroupDataAsset`
```python
{
    "id": obj["Name"],
    "items": [
        {
            "dungeon_grade": item.get("DungeonGrade"),
            "loot_drop_id": _extract_asset_id(item.get("LootDropId")),
            "loot_drop_rate_id": _extract_asset_id(item.get("LootDropRateId")),
            "loot_drop_count": item.get("LootDropCount"),
        }
        for item in (props.get("LootDropGroupItemArray") or [])
    ],
}
```

#### `extract_loot_drop_rates.py` — `DCLootDropRateDataAsset`
```python
{
    "id": obj["Name"],
    "rates": [
        {
            "luck_grade": item.get("LuckGrade"),
            "drop_rate": item.get("DropRate"),
        }
        for item in (props.get("LootDropRateItemArray") or [])
    ],
}
```

---

## 5. Orchestrators

### 5.1 `dungeons/__init__.py`

```python
_V2_BASE = "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2"

def run(raw_root, extracted_root):
    dirs = {
        "dungeon":             raw_root / _V2_BASE / "Dungeon" / "Dungeon",
        "dungeon_type":        raw_root / _V2_BASE / "Dungeon" / "DungeonType",
        "dungeon_grade":       raw_root / _V2_BASE / "Dungeon" / "DungeonGrade",
        "dungeon_card":        raw_root / _V2_BASE / "Dungeon" / "DungeonCard",
        "dungeon_layout":      raw_root / _V2_BASE / "Dungeon" / "DungeonLayout",
        "dungeon_module":      raw_root / _V2_BASE / "Dungeon" / "DungeonModule",
        "floor_rule":          raw_root / _V2_BASE / "FloorRule",
        "props":               raw_root / _V2_BASE / "Props" / "Props",
        "props_effect":        raw_root / _V2_BASE / "Props" / "PropsEffect",
        "props_interact":      raw_root / _V2_BASE / "Props" / "PropsInteract",
        "props_skill_check":   raw_root / _V2_BASE / "Props" / "PropsSkillCheck",
        "map_icon":            raw_root / _V2_BASE / "MapIcon" / "MapIcon",
        "vehicle":             raw_root / _V2_BASE / "Vehicle",
    }
```

Each `run_*()` function returns `{id: entity}`. The orchestrator accumulates all
entities into `all_entities` with `_entity_type` tag, then writes a single combined
`_index.json` with `{"id", "type"}` per entry (no `name` — many dungeon sub-types
have no name field). Follows the `combat` domain pattern exactly.

The `run()` return dict uses these summary keys:

```
"dungeons", "dungeon_types", "dungeon_grades", "dungeon_cards",
"dungeon_layouts", "dungeon_modules", "floor_rules", "props",
"props_effects", "props_interacts", "props_skill_checks",
"map_icons", "vehicles"
```

### 5.2 `spawns/__init__.py`

Same pattern. Combined index entries: `{"id", "type"}`.

The `run()` return dict uses these summary keys:

```
"spawners", "loot_drops", "loot_drop_groups", "loot_drop_rates"
```

---

## 6. `_extract_asset_id` helper

`extract_dungeons.py`, `extract_spawners.py`, `extract_loot_drops.py`, and
`extract_loot_drop_groups.py` all resolve `{AssetPathName, SubPathString}` references.
`extract_vehicles.py` also requires it for `SwimmingMovementModifier`.
Each of these files defines its own local `_extract_asset_id()`:

```python
def _extract_asset_id(ref: dict) -> str | None:
    if not isinstance(ref, dict):
        return None
    asset_path = ref.get("AssetPathName", "")
    if not asset_path:
        return None
    parts = asset_path.split(".")
    return parts[-1] if len(parts) > 1 else None
```

This is identical to the helper in `extract_aoes.py` (and the fix applied in Phase 3
to guard `len(parts) > 1`).

---

## 7. Testing Strategy

### Unit tests (per extractor)

Each test file:
1. `make_<entity>_file(tmp_path, id, ...)` fixture helper
2. `test_extract_<entity>_returns_id_and_fields` — call `extract_*()`, assert fields
3. `test_extract_<entity>_returns_none_for_wrong_type` — wrong Type value → None
4. `test_run_<entity>s_writes_entity_and_index` — call `run_*()`, assert entity file
   exists, content correct, `_meta` present, `_index.json` exists, id in return dict

For `extract_dungeon_cards.py` and `extract_map_icons.py`: tests only assert `id` is
present (no Properties to verify).

For `extract_floor_rules.py` and `extract_vehicles.py`: tests cover each sub-type
function and the combined `run_*()`.

### Integration tests

`test_dungeons_integration.py`:
```python
@pytest.mark.skipif(not DUNGEON_DIR.exists(), reason="raw data not present")
def test_dungeons_run_integration(tmp_path):
    summary = run(raw_root=RAW_ROOT, extracted_root=tmp_path)
    assert summary["dungeons"] > 100
    assert summary["props"] > 800
    # ... counts for all 13 sub-types
    index = tmp_path / "dungeons" / "_index.json"
    entity_types = {e["type"] for e in index_data["entries"]}
    # assert all _entity_type values present
```

`test_spawns_integration.py`:
```python
@pytest.mark.skipif(not SPAWNER_DIR.exists(), reason="raw data not present")
def test_spawns_run_integration(tmp_path):
    summary = run(raw_root=RAW_ROOT, extracted_root=tmp_path)
    assert summary["spawners"] > 400
    assert summary["loot_drops"] > 2000
    assert summary["loot_drop_groups"] > 300
    assert summary["loot_drop_rates"] > 2000
```

---

## 8. Output layout

```
extracted/
    dungeons/
        _index.json                        ← combined, all entity types
        Id_Dungeon_Crypts_A.json
        Id_DungeonType_Crypts_A.json
        Id_DungeonGrade_Arena.json
        ...
    spawns/
        _index.json                        ← combined, all entity types
        Id_Spawner_Lootdrop_Anchor.json
        ID_Lootdrop_CaveTrollsPreciousRock.json
        ...
```

All entity files follow the standard `{...fields..., "_meta": {...}}` format written
by `Writer.write_entity()`.

---

## 9. Out of scope

- `Props/PropsAbility/` — `DCGameplayAbilityDataAsset`, skipped
- `Vehicle/VehicleAbility/` — `DCGameplayAbilityDataAsset`, skipped
- Blueprint-level logic (C++ AttributeSet, ability graphs)
- `Dungeon.Layouts` array — malformed AssetPathName values in source data, not extracted
