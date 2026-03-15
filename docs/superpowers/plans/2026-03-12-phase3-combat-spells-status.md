# Phase 3: Combat, Spells, Status Domains — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract all combat (MeleeAttack, Projectile, Aoe, MovementModifier, GEModifier), spells (Spell, Religion, FaustianBargain), and status (ActorStatus × 4 categories) systems into `extracted/` JSON.

**Architecture:** Three domain packages following the established `pipeline/domains/<domain>/` pattern. Status uses the combined-index pattern from classes (4 category subtypes share one extractor + orchestrator merges index). MovementModifier produces both entity files and a `extracted/combat/movement.json` system file per spec §2.1.

**Tech Stack:** Python 3.11, pytest, pipeline.core library (reader, normalizer, writer)

---

## File Structure

**New files:**
```
pipeline/domains/combat/__init__.py              # orchestrator run()
pipeline/domains/combat/extract_melee_attacks.py # DCMeleeAttackDataAsset
pipeline/domains/combat/extract_movement_modifiers.py  # DCMovementModifierDataAsset
pipeline/domains/combat/extract_ge_modifiers.py  # DCGEModifierDataAsset
pipeline/domains/combat/extract_projectiles.py   # DCProjectileDataAsset
pipeline/domains/combat/extract_aoes.py          # DCAoeDataAsset

pipeline/domains/spells/__init__.py              # orchestrator run()
pipeline/domains/spells/extract_spells.py        # DCSpellDataAsset
pipeline/domains/spells/extract_religions.py     # DCReligionDataAsset
pipeline/domains/spells/extract_faustian_bargains.py  # DCFaustianBargainDataAsset

pipeline/domains/status/__init__.py              # orchestrator run(), combined-index
pipeline/domains/status/extract_status_effects.py  # DCGameplayEffectDataAsset × 4 categories

tests/domains/combat/__init__.py
tests/domains/combat/test_extract_melee_attacks.py
tests/domains/combat/test_extract_movement_modifiers.py
tests/domains/combat/test_extract_ge_modifiers.py
tests/domains/combat/test_extract_projectiles.py
tests/domains/combat/test_extract_aoes.py
tests/domains/combat/test_combat_integration.py

tests/domains/spells/__init__.py
tests/domains/spells/test_extract_spells.py
tests/domains/spells/test_extract_religions.py
tests/domains/spells/test_extract_faustian_bargains.py
tests/domains/spells/test_spells_integration.py

tests/domains/status/__init__.py
tests/domains/status/test_extract_status_effects.py
tests/domains/status/test_status_integration.py
```

**Raw data directories (confirmed from exploration):**
```
V2/MeleeAttack/MeleeAttack/           → DCMeleeAttackDataAsset  (182 files)
V2/Projectile/{Projectile,ProjectileAbility,ProjectileEffect}/  → DCProjectileDataAsset (113) + other types (skip)
V2/Aoe/Aoe/                           → DCAoeDataAsset (49) + other types (skip)
V2/MovementModifier/MovementModifier/  → DCMovementModifierDataAsset (318 files)
V2/GEModifier/GEModifier/             → DCGEModifierDataAsset (18 files)

V2/Spell/Spell/                        → DCSpellDataAsset (81 files)
V2/Religion/Religion/                  → DCReligionDataAsset (33 files)
V2/FaustianBargain/FaustianBargain/   → DCFaustianBargainDataAsset (156 files)

V2/ActorStatus/StatusEffect/           → DCGameplayEffectDataAsset (810 files)
V2/ActorStatusMonster/StatusEffect/    → DCGameplayEffectDataAsset (158 files)
V2/ActorStatusInWater/StatusEffect/    → DCGameplayEffectDataAsset (9 files)
V2/ActorStatusItemCosmetic/StatusEffect/ → DCGameplayEffectDataAsset (30 files)
```

---

## Chunk 1: Combat Domain

### Task 1: Scaffold Combat Domain

**Files:**
- Create: `pipeline/domains/combat/__init__.py`
- Create: `tests/domains/combat/__init__.py`

- [ ] **Step 1: Create the combat package with a stub `run()`**

```python
# pipeline/domains/combat/__init__.py
"""Combat domain extractor — run() called by extract_all.py orchestrator."""
from pathlib import Path

_V2_BASE = "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2"


def run(raw_root: Path, extracted_root: Path) -> dict:
    """Run all combat domain extractors. Returns summary of counts."""
    print("[combat] Starting extraction...")
    summary = {}
    print(f"[combat] Done. Summary: {summary}")
    return summary
```

- [ ] **Step 2: Create empty test package**

```
tests/domains/combat/__init__.py  (empty file)
```

- [ ] **Step 3: Verify import works**

Run: `cd darkanddarker-wiki && pytest tests/domains/combat/ -v`
Expected: `no tests ran` (0 collected, no errors)

- [ ] **Step 4: Commit**

```bash
git add pipeline/domains/combat/__init__.py tests/domains/combat/__init__.py
git commit -m "feat(combat): scaffold combat domain package"
```

---

### Task 2: Extract Melee Attacks

**Files:**
- Create: `pipeline/domains/combat/extract_melee_attacks.py`
- Create: `tests/domains/combat/test_extract_melee_attacks.py`

**Raw data:** `V2/MeleeAttack/MeleeAttack/Id_MeleeAttack_*.json`
**Type:** `DCMeleeAttackDataAsset`
**Props confirmed from data:** HitPlayRate (float), HitPlayRateDuration (float), ComboTypeTag (TagName), CanStuckByStaticObject (bool), WeakShieldStuckPlayRateDuration (float), StaticObjectStuckPlayRate (float)

- [ ] **Step 1: Write the failing tests**

```python
# tests/domains/combat/test_extract_melee_attacks.py
"""Tests for pipeline/domains/combat/extract_melee_attacks.py"""
import json
from pathlib import Path
from pipeline.domains.combat.extract_melee_attacks import (
    extract_melee_attack, run_melee_attacks
)


def make_melee_file(tmp_path, attack_id):
    data = [{
        "Type": "DCMeleeAttackDataAsset",
        "Name": attack_id,
        "Properties": {
            "HitPlayRate": 1.2,
            "HitPlayRateDuration": 0.5,
            "ComboTypeTag": {"TagName": "ComboType.Sword.Normal"},
            "CanStuckByStaticObject": True,
            "WeakShieldStuckPlayRateDuration": 0.3,
            "StaticObjectStuckPlayRate": 0.8,
        }
    }]
    f = tmp_path / f"{attack_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_melee_attack_returns_id_and_fields(tmp_path):
    f = make_melee_file(tmp_path, "Id_MeleeAttack_GA_ArmingSwordAttack01")
    result = extract_melee_attack(f)
    assert result is not None
    assert result["id"] == "Id_MeleeAttack_GA_ArmingSwordAttack01"
    assert result["hit_play_rate"] == 1.2
    assert result["hit_play_rate_duration"] == 0.5
    assert result["combo_type_tag"] == "ComboType.Sword.Normal"
    assert result["can_stuck_by_static_object"] is True


def test_extract_melee_attack_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "Other"}]', encoding="utf-8")
    assert extract_melee_attack(f) is None


def test_run_melee_attacks_writes_entity_and_index(tmp_path):
    melee_dir = tmp_path / "melee"
    melee_dir.mkdir()
    make_melee_file(melee_dir, "Id_MeleeAttack_GA_ArmingSwordAttack01")
    extracted = tmp_path / "extracted"
    result = run_melee_attacks(melee_dir=melee_dir, extracted_root=extracted)
    entity = extracted / "combat" / "Id_MeleeAttack_GA_ArmingSwordAttack01.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["combo_type_tag"] == "ComboType.Sword.Normal"
    assert "_meta" in data
    index = extracted / "combat" / "_index.json"
    assert index.exists()
    assert "Id_MeleeAttack_GA_ArmingSwordAttack01" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/domains/combat/test_extract_melee_attacks.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline.domains.combat.extract_melee_attacks'`

- [ ] **Step 3: Implement `extract_melee_attacks.py`**

```python
# pipeline/domains/combat/extract_melee_attacks.py
"""Extract DCMeleeAttackDataAsset files → extracted/combat/<id>.json + _index.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_tag, camel_to_snake
from pipeline.core.writer import Writer


def extract_melee_attack(file_path: Path) -> dict | None:
    """Extract one DCMeleeAttackDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCMeleeAttackDataAsset"), None)
    if not obj:
        return None

    attack_id = obj.get("Name", file_path.stem)
    props = get_properties(obj)

    return {
        "id": attack_id,
        "hit_play_rate": props.get("HitPlayRate"),
        "hit_play_rate_duration": props.get("HitPlayRateDuration"),
        "combo_type_tag": resolve_tag(props.get("ComboTypeTag")),
        "can_stuck_by_static_object": props.get("CanStuckByStaticObject", False),
        "weak_shield_stuck_play_rate_duration": props.get("WeakShieldStuckPlayRateDuration"),
        "static_object_stuck_play_rate": props.get("StaticObjectStuckPlayRate"),
        "static_object_stuck_play_rate_duration": props.get("StaticObjectStuckPlayRateDuration"),
    }


def run_melee_attacks(melee_dir: Path, extracted_root: Path) -> dict:
    """Extract all MeleeAttack files → extracted/combat/<id>.json + _index.json."""
    files = find_files(str(Path(melee_dir) / "Id_MeleeAttack_*.json"))
    print(f"  [melee_attacks] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    attacks = {}

    for f in files:
        result = extract_melee_attack(f)
        if not result:
            continue
        attack_id = result["id"]
        attacks[attack_id] = result
        writer.write_entity("combat", attack_id, result, source_files=[str(f)])
        index_entries.append({
            "id": attack_id,
            "combo_type_tag": result.get("combo_type_tag"),
        })

    writer.write_index("combat", index_entries)
    print(f"  [melee_attacks] Extracted {len(attacks)} melee attacks")
    return attacks
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/domains/combat/test_extract_melee_attacks.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/combat/extract_melee_attacks.py tests/domains/combat/test_extract_melee_attacks.py
git commit -m "feat(combat): extract MeleeAttack domain"
```

---

### Task 3: Extract Movement Modifiers

**Files:**
- Create: `pipeline/domains/combat/extract_movement_modifiers.py`
- Create: `tests/domains/combat/test_extract_movement_modifiers.py`

**Raw data:** `V2/MovementModifier/MovementModifier/Id_MovementModifier_*.json`
**Type:** `DCMovementModifierDataAsset`
**Props confirmed:** Multiply (float), JumpZMultiply (float), GravityScaleMultiply (float)
**Outputs:** entity files per modifier (extracted/combat/<id>.json) **AND** system file `extracted/combat/movement.json` (per spec §2.1 and pre-spec movement.json notes)

- [ ] **Step 1: Write the failing tests**

```python
# tests/domains/combat/test_extract_movement_modifiers.py
"""Tests for pipeline/domains/combat/extract_movement_modifiers.py"""
import json
from pathlib import Path
from pipeline.domains.combat.extract_movement_modifiers import (
    extract_movement_modifier, run_movement_modifiers
)


def make_mm_file(tmp_path, mm_id, multiply=0.65, jump_z=0.0, gravity=0.0):
    data = [{
        "Type": "DCMovementModifierDataAsset",
        "Name": mm_id,
        "Properties": {
            "Multiply": multiply,
            "JumpZMultiply": jump_z,
            "GravityScaleMultiply": gravity,
        }
    }]
    f = tmp_path / f"{mm_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_movement_modifier_returns_id_and_fields(tmp_path):
    f = make_mm_file(tmp_path, "Id_MovementModifier_Crouch", multiply=0.65)
    result = extract_movement_modifier(f)
    assert result is not None
    assert result["id"] == "Id_MovementModifier_Crouch"
    assert result["multiply"] == 0.65
    assert result["jump_z_multiply"] == 0.0
    assert result["gravity_scale_multiply"] == 0.0


def test_extract_movement_modifier_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "Other"}]', encoding="utf-8")
    assert extract_movement_modifier(f) is None


def test_run_movement_modifiers_writes_entity_and_index(tmp_path):
    mm_dir = tmp_path / "mm"
    mm_dir.mkdir()
    make_mm_file(mm_dir, "Id_MovementModifier_Crouch")
    extracted = tmp_path / "extracted"
    result = run_movement_modifiers(mm_dir=mm_dir, extracted_root=extracted)
    entity = extracted / "combat" / "Id_MovementModifier_Crouch.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["multiply"] == 0.65
    assert "_meta" in data
    index = extracted / "combat" / "_index.json"
    assert index.exists()
    assert "Id_MovementModifier_Crouch" in result


def test_run_movement_modifiers_writes_system_file(tmp_path):
    mm_dir = tmp_path / "mm"
    mm_dir.mkdir()
    make_mm_file(mm_dir, "Id_MovementModifier_Crouch", multiply=0.65)
    make_mm_file(mm_dir, "Id_MovementModifier_Walk", multiply=0.4)
    extracted = tmp_path / "extracted"
    run_movement_modifiers(mm_dir=mm_dir, extracted_root=extracted)
    system_file = extracted / "combat" / "movement.json"
    assert system_file.exists()
    data = json.loads(system_file.read_text(encoding="utf-8"))
    assert "modifiers" in data
    assert "Id_MovementModifier_Crouch" in data["modifiers"]
    assert data["modifiers"]["Id_MovementModifier_Crouch"]["multiply"] == 0.65
    assert "_meta" in data
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/domains/combat/test_extract_movement_modifiers.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `extract_movement_modifiers.py`**

```python
# pipeline/domains/combat/extract_movement_modifiers.py
"""Extract DCMovementModifierDataAsset → entity files + extracted/combat/movement.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.writer import Writer


def extract_movement_modifier(file_path: Path) -> dict | None:
    """Extract one DCMovementModifierDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCMovementModifierDataAsset"), None)
    if not obj:
        return None

    mm_id = obj.get("Name", file_path.stem)
    props = get_properties(obj)

    return {
        "id": mm_id,
        "multiply": props.get("Multiply"),
        "jump_z_multiply": props.get("JumpZMultiply"),
        "gravity_scale_multiply": props.get("GravityScaleMultiply"),
    }


def run_movement_modifiers(mm_dir: Path, extracted_root: Path) -> dict:
    """Extract all MovementModifier files → entity files + movement.json system file."""
    files = find_files(str(Path(mm_dir) / "Id_MovementModifier_*.json"))
    print(f"  [movement_modifiers] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    modifiers = {}

    for f in files:
        result = extract_movement_modifier(f)
        if not result:
            continue
        mm_id = result["id"]
        modifiers[mm_id] = result
        writer.write_entity("combat", mm_id, result, source_files=[str(f)])
        index_entries.append({"id": mm_id, "multiply": result.get("multiply")})

    writer.write_index("combat", index_entries)

    # Write system file aggregating all modifiers (spec §2.1 canonical movement.json)
    system_data = {
        "modifiers": {
            mm_id: {
                "multiply": v["multiply"],
                "jump_z_multiply": v["jump_z_multiply"],
                "gravity_scale_multiply": v["gravity_scale_multiply"],
            }
            for mm_id, v in modifiers.items()
        }
    }
    writer.write_system("combat", "movement", system_data)

    print(f"  [movement_modifiers] Extracted {len(modifiers)} modifiers")
    return modifiers
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/domains/combat/test_extract_movement_modifiers.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/combat/extract_movement_modifiers.py tests/domains/combat/test_extract_movement_modifiers.py
git commit -m "feat(combat): extract MovementModifier + write movement.json system file"
```

---

### Task 4: Extract GE Modifiers

**Files:**
- Create: `pipeline/domains/combat/extract_ge_modifiers.py`
- Create: `tests/domains/combat/test_extract_ge_modifiers.py`

**Raw data:** `V2/GEModifier/GEModifier/*.json`
**Type:** `DCGEModifierDataAsset`
**Props confirmed:** TargetGameplayEffectTag (TagName), EffectType (TagName), Add (float)

- [ ] **Step 1: Write the failing tests**

```python
# tests/domains/combat/test_extract_ge_modifiers.py
"""Tests for pipeline/domains/combat/extract_ge_modifiers.py"""
import json
from pathlib import Path
from pipeline.domains.combat.extract_ge_modifiers import (
    extract_ge_modifier, run_ge_modifiers
)


def make_ge_file(tmp_path, ge_id):
    data = [{
        "Type": "DCGEModifierDataAsset",
        "Name": ge_id,
        "Properties": {
            "TargetGameplayEffectTag": {"TagName": "State.ActorStatus.Buff.SacredWater"},
            "EffectType": {"TagName": "Type.GEMod.Source"},
            "Add": 1.5,
        }
    }]
    f = tmp_path / f"{ge_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_ge_modifier_returns_id_and_fields(tmp_path):
    f = make_ge_file(tmp_path, "Id_GEModifier_BrewMaster")
    result = extract_ge_modifier(f)
    assert result is not None
    assert result["id"] == "Id_GEModifier_BrewMaster"
    assert result["target_gameplay_effect_tag"] == "State.ActorStatus.Buff.SacredWater"
    assert result["effect_type"] == "Type.GEMod.Source"
    assert result["add"] == 1.5


def test_extract_ge_modifier_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "Other"}]', encoding="utf-8")
    assert extract_ge_modifier(f) is None


def test_run_ge_modifiers_writes_entity_and_index(tmp_path):
    ge_dir = tmp_path / "ge"
    ge_dir.mkdir()
    make_ge_file(ge_dir, "Id_GEModifier_BrewMaster")
    extracted = tmp_path / "extracted"
    result = run_ge_modifiers(ge_dir=ge_dir, extracted_root=extracted)
    entity = extracted / "combat" / "Id_GEModifier_BrewMaster.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["target_gameplay_effect_tag"] == "State.ActorStatus.Buff.SacredWater"
    assert "_meta" in data
    index = extracted / "combat" / "_index.json"
    assert index.exists()
    assert "Id_GEModifier_BrewMaster" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/domains/combat/test_extract_ge_modifiers.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `extract_ge_modifiers.py`**

```python
# pipeline/domains/combat/extract_ge_modifiers.py
"""Extract DCGEModifierDataAsset files → extracted/combat/<id>.json + _index.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_tag
from pipeline.core.writer import Writer


def extract_ge_modifier(file_path: Path) -> dict | None:
    """Extract one DCGEModifierDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCGEModifierDataAsset"), None)
    if not obj:
        return None

    ge_id = obj.get("Name", file_path.stem)
    props = get_properties(obj)

    return {
        "id": ge_id,
        "target_gameplay_effect_tag": resolve_tag(props.get("TargetGameplayEffectTag")),
        "effect_type": resolve_tag(props.get("EffectType")),
        "add": props.get("Add"),
    }


def run_ge_modifiers(ge_dir: Path, extracted_root: Path) -> dict:
    """Extract all GEModifier files → extracted/combat/<id>.json + _index.json."""
    files = find_files(str(Path(ge_dir) / "*.json"))
    print(f"  [ge_modifiers] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    modifiers = {}

    for f in files:
        result = extract_ge_modifier(f)
        if not result:
            continue
        ge_id = result["id"]
        modifiers[ge_id] = result
        writer.write_entity("combat", ge_id, result, source_files=[str(f)])
        index_entries.append({
            "id": ge_id,
            "target_gameplay_effect_tag": result.get("target_gameplay_effect_tag"),
            "effect_type": result.get("effect_type"),
        })

    writer.write_index("combat", index_entries)
    print(f"  [ge_modifiers] Extracted {len(modifiers)} GE modifiers")
    return modifiers
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/domains/combat/test_extract_ge_modifiers.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/combat/extract_ge_modifiers.py tests/domains/combat/test_extract_ge_modifiers.py
git commit -m "feat(combat): extract GEModifier domain"
```

---

### Task 5: Extract Projectiles

**Files:**
- Create: `pipeline/domains/combat/extract_projectiles.py`
- Create: `tests/domains/combat/test_extract_projectiles.py`

**Raw data:** `V2/Projectile/**/*.json` (3 subdirs; also contains DCGameplayAbilityDataAsset — skip by type filter)
**Type:** `DCProjectileDataAsset` (113 files; type filter skips the 74 other-type files)
**Props from spec:** SourceTypes (list of tags)

- [ ] **Step 1: Inspect a sample projectile for field names**

Run: `cd darkanddarker-wiki && py -c "import json,pathlib; d=pathlib.Path('raw/DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/Projectile/Projectile'); f=sorted(d.glob('*.json'))[0]; s=json.loads(f.read_text(encoding='utf-8')); [print(o['Name'], list(o.get('Properties',{}).keys())[:10]) for o in s if isinstance(o,dict) and o.get('Type')=='DCProjectileDataAsset']"`

- [ ] **Step 2: Write the failing tests**

```python
# tests/domains/combat/test_extract_projectiles.py
"""Tests for pipeline/domains/combat/extract_projectiles.py"""
import json
from pathlib import Path
from pipeline.domains.combat.extract_projectiles import (
    extract_projectile, run_projectiles
)


def make_projectile_file(tmp_path, proj_id):
    data = [{
        "Type": "DCProjectileDataAsset",
        "Name": proj_id,
        "Properties": {
            "SourceTypes": [
                {"TagName": "Source.Ranged.Arrow"},
                {"TagName": "Source.Ranged.Magic"},
            ],
        }
    }]
    f = tmp_path / f"{proj_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_projectile_returns_id_and_fields(tmp_path):
    f = make_projectile_file(tmp_path, "Id_Projectile_Arrow")
    result = extract_projectile(f)
    assert result is not None
    assert result["id"] == "Id_Projectile_Arrow"
    assert "Source.Ranged.Arrow" in result["source_types"]


def test_extract_projectile_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCGameplayAbilityDataAsset"}]', encoding="utf-8")
    assert extract_projectile(f) is None


def test_run_projectiles_writes_entity_and_index(tmp_path):
    proj_dir = tmp_path / "projectile"
    proj_dir.mkdir()
    make_projectile_file(proj_dir, "Id_Projectile_Arrow")
    extracted = tmp_path / "extracted"
    result = run_projectiles(projectile_dir=proj_dir, extracted_root=extracted)
    entity = extracted / "combat" / "Id_Projectile_Arrow.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert "source_types" in data
    assert "_meta" in data
    index = extracted / "combat" / "_index.json"
    assert index.exists()
    assert "Id_Projectile_Arrow" in result
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/domains/combat/test_extract_projectiles.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implement `extract_projectiles.py`**

```python
# pipeline/domains/combat/extract_projectiles.py
"""Extract DCProjectileDataAsset files → extracted/combat/<id>.json + _index.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_tag
from pipeline.core.writer import Writer


def extract_projectile(file_path: Path) -> dict | None:
    """Extract one DCProjectileDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCProjectileDataAsset"), None)
    if not obj:
        return None

    proj_id = obj.get("Name", file_path.stem)
    props = get_properties(obj)

    source_types = [
        resolve_tag(t) for t in (props.get("SourceTypes") or [])
        if resolve_tag(t) is not None
    ]

    return {
        "id": proj_id,
        "source_types": source_types,
    }


def run_projectiles(projectile_dir: Path, extracted_root: Path) -> dict:
    """Extract all Projectile files → extracted/combat/<id>.json + _index.json.

    NOTE: The Projectile V2 directory also contains DCGameplayAbilityDataAsset and
    DCGameplayEffectDataAsset files. extract_projectile() skips them via type filter.
    """
    files = find_files(str(Path(projectile_dir) / "**" / "*.json"))
    print(f"  [projectiles] Found {len(files)} files (will skip non-DCProjectileDataAsset)")

    writer = Writer(extracted_root)
    index_entries = []
    projectiles = {}

    for f in files:
        result = extract_projectile(f)
        if not result:
            continue
        proj_id = result["id"]
        projectiles[proj_id] = result
        writer.write_entity("combat", proj_id, result, source_files=[str(f)])
        index_entries.append({
            "id": proj_id,
            "source_types": result.get("source_types"),
        })

    writer.write_index("combat", index_entries)
    print(f"  [projectiles] Extracted {len(projectiles)} projectiles")
    return projectiles
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/domains/combat/test_extract_projectiles.py -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add pipeline/domains/combat/extract_projectiles.py tests/domains/combat/test_extract_projectiles.py
git commit -m "feat(combat): extract Projectile domain"
```

---

### Task 6: Extract AOEs

**Files:**
- Create: `pipeline/domains/combat/extract_aoes.py`
- Create: `tests/domains/combat/test_extract_aoes.py`

**Raw data:** `V2/Aoe/Aoe/Id_Aoe_*.json` (also contains DCGameplayAbilityDataAsset — skip by type filter)
**Type:** `DCAoeDataAsset` (49 files)
**Props confirmed:** ArtData (asset ref dict), SoundData (asset ref dict), Abilities (list of asset refs)

- [ ] **Step 1: Write the failing tests**

```python
# tests/domains/combat/test_extract_aoes.py
"""Tests for pipeline/domains/combat/extract_aoes.py"""
import json
from pathlib import Path
from pipeline.domains.combat.extract_aoes import extract_aoe, run_aoes


def make_aoe_file(tmp_path, aoe_id):
    data = [{
        "Type": "DCAoeDataAsset",
        "Name": aoe_id,
        "Properties": {
            "ArtData": {"AssetPathName": "/Game/.../GA_AoeArt.GA_AoeArt", "SubPathString": ""},
            "SoundData": {"AssetPathName": "/Game/.../GA_AoeSound.GA_AoeSound", "SubPathString": ""},
            "Abilities": [
                {"AssetPathName": "/Game/.../GA_AoeAbility.GA_AoeAbility", "SubPathString": ""}
            ],
        }
    }]
    f = tmp_path / f"{aoe_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_aoe_returns_id_and_fields(tmp_path):
    f = make_aoe_file(tmp_path, "Id_Aoe_IceShardArea")
    result = extract_aoe(f)
    assert result is not None
    assert result["id"] == "Id_Aoe_IceShardArea"
    assert result["art_data"] is not None
    assert result["sound_data"] is not None
    assert isinstance(result["abilities"], list)


def test_extract_aoe_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCGameplayAbilityDataAsset"}]', encoding="utf-8")
    assert extract_aoe(f) is None


def test_run_aoes_writes_entity_and_index(tmp_path):
    aoe_dir = tmp_path / "aoe"
    aoe_dir.mkdir()
    make_aoe_file(aoe_dir, "Id_Aoe_IceShardArea")
    extracted = tmp_path / "extracted"
    result = run_aoes(aoe_dir=aoe_dir, extracted_root=extracted)
    entity = extracted / "combat" / "Id_Aoe_IceShardArea.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert "abilities" in data
    assert "_meta" in data
    index = extracted / "combat" / "_index.json"
    assert index.exists()
    assert "Id_Aoe_IceShardArea" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/domains/combat/test_extract_aoes.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `extract_aoes.py`**

```python
# pipeline/domains/combat/extract_aoes.py
"""Extract DCAoeDataAsset files → extracted/combat/<id>.json + _index.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_ref
from pipeline.core.writer import Writer


def extract_aoe(file_path: Path) -> dict | None:
    """Extract one DCAoeDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCAoeDataAsset"), None)
    if not obj:
        return None

    aoe_id = obj.get("Name", file_path.stem)
    props = get_properties(obj)

    abilities = [
        resolve_ref(a) for a in (props.get("Abilities") or [])
        if resolve_ref(a) is not None
    ]

    return {
        "id": aoe_id,
        "art_data": resolve_ref(props.get("ArtData")),
        "sound_data": resolve_ref(props.get("SoundData")),
        "abilities": abilities,
    }


def run_aoes(aoe_dir: Path, extracted_root: Path) -> dict:
    """Extract all Aoe files → extracted/combat/<id>.json + _index.json.

    NOTE: The Aoe V2 directory also contains DCGameplayAbilityDataAsset files.
    extract_aoe() skips them via type filter.
    """
    files = find_files(str(Path(aoe_dir) / "Id_Aoe_*.json"))
    print(f"  [aoes] Found {len(files)} files (will skip non-DCAoeDataAsset)")

    writer = Writer(extracted_root)
    index_entries = []
    aoes = {}

    for f in files:
        result = extract_aoe(f)
        if not result:
            continue
        aoe_id = result["id"]
        aoes[aoe_id] = result
        writer.write_entity("combat", aoe_id, result, source_files=[str(f)])
        index_entries.append({"id": aoe_id})

    writer.write_index("combat", index_entries)
    print(f"  [aoes] Extracted {len(aoes)} AOEs")
    return aoes
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/domains/combat/test_extract_aoes.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/combat/extract_aoes.py tests/domains/combat/test_extract_aoes.py
git commit -m "feat(combat): extract Aoe domain"
```

---

### Task 7: Combat Orchestrator + Integration Test

**Files:**
- Modify: `pipeline/domains/combat/__init__.py`
- Create: `tests/domains/combat/test_combat_integration.py`

**Integration test reads real data from:** `raw/DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/MeleeAttack/MeleeAttack/`

- [ ] **Step 1: Write the failing integration test**

```python
# tests/domains/combat/test_combat_integration.py
"""Integration test: run combat domain against real raw data."""
import json
from pathlib import Path
import pytest
from pipeline.domains.combat import run

RAW_ROOT = Path("raw")
MELEE_DIR = RAW_ROOT / "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/MeleeAttack/MeleeAttack"


@pytest.mark.skipif(not MELEE_DIR.exists(), reason="raw data not present")
def test_combat_run_integration(tmp_path):
    summary = run(raw_root=RAW_ROOT, extracted_root=tmp_path)
    assert summary.get("melee_attacks", 0) > 100
    assert summary.get("movement_modifiers", 0) > 200
    assert summary.get("ge_modifiers", 0) > 0
    assert summary.get("projectiles", 0) > 50
    assert summary.get("aoes", 0) > 20
    index = tmp_path / "combat" / "_index.json"
    assert index.exists()
    index_data = json.loads(index.read_text(encoding="utf-8"))
    entity_types = {e["type"] for e in index_data["entries"]}
    assert "melee_attack" in entity_types
    assert "movement_modifier" in entity_types
    assert "projectile" in entity_types
    movement = tmp_path / "combat" / "movement.json"
    assert movement.exists()
    data = json.loads(movement.read_text(encoding="utf-8"))
    assert len(data["modifiers"]) > 10
```

- [ ] **Step 2: Run integration test to see current failure**

Run: `pytest tests/domains/combat/test_combat_integration.py -v`
Expected: FAIL — `assert summary.get("melee_attacks", 0) > 100` (run() returns empty summary)

- [ ] **Step 3: Implement the combat orchestrator**

```python
# pipeline/domains/combat/__init__.py
"""Combat domain extractor — run() called by extract_all.py orchestrator."""
from pathlib import Path

from pipeline.domains.combat.extract_melee_attacks import run_melee_attacks
from pipeline.domains.combat.extract_movement_modifiers import run_movement_modifiers
from pipeline.domains.combat.extract_ge_modifiers import run_ge_modifiers
from pipeline.domains.combat.extract_projectiles import run_projectiles
from pipeline.domains.combat.extract_aoes import run_aoes
from pipeline.core.writer import Writer

_V2_BASE = "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2"


def run(raw_root: Path, extracted_root: Path) -> dict:
    """Run all combat domain extractors. Returns summary of counts.

    NOTE: Individual run_* functions each write a partial _index.json as a
    side-effect (useful for standalone runs / unit tests). This orchestrator
    overwrites that partial index with a single combined index containing all
    entity types at the end.
    """
    print("[combat] Starting extraction...")
    summary = {}
    all_entities: dict[str, dict] = {}

    dirs = {
        "melee": raw_root / _V2_BASE / "MeleeAttack" / "MeleeAttack",
        "mm": raw_root / _V2_BASE / "MovementModifier" / "MovementModifier",
        "ge": raw_root / _V2_BASE / "GEModifier" / "GEModifier",
        "projectile": raw_root / _V2_BASE / "Projectile",
        "aoe": raw_root / _V2_BASE / "Aoe" / "Aoe",
    }

    if dirs["melee"].exists():
        attacks = run_melee_attacks(melee_dir=dirs["melee"], extracted_root=extracted_root)
        summary["melee_attacks"] = len(attacks)
        all_entities.update({k: {**v, "_entity_type": "melee_attack"}
                             for k, v in attacks.items()})
    else:
        print(f"  [combat] WARNING: {dirs['melee']} not found")
        summary["melee_attacks"] = 0

    if dirs["mm"].exists():
        mms = run_movement_modifiers(mm_dir=dirs["mm"], extracted_root=extracted_root)
        summary["movement_modifiers"] = len(mms)
        all_entities.update({k: {**v, "_entity_type": "movement_modifier"}
                             for k, v in mms.items()})
    else:
        print(f"  [combat] WARNING: {dirs['mm']} not found")
        summary["movement_modifiers"] = 0

    if dirs["ge"].exists():
        ges = run_ge_modifiers(ge_dir=dirs["ge"], extracted_root=extracted_root)
        summary["ge_modifiers"] = len(ges)
        all_entities.update({k: {**v, "_entity_type": "ge_modifier"}
                             for k, v in ges.items()})
    else:
        print(f"  [combat] WARNING: {dirs['ge']} not found")
        summary["ge_modifiers"] = 0

    if dirs["projectile"].exists():
        projs = run_projectiles(projectile_dir=dirs["projectile"], extracted_root=extracted_root)
        summary["projectiles"] = len(projs)
        all_entities.update({k: {**v, "_entity_type": "projectile"}
                             for k, v in projs.items()})
    else:
        print(f"  [combat] WARNING: {dirs['projectile']} not found")
        summary["projectiles"] = 0

    if dirs["aoe"].exists():
        aoes = run_aoes(aoe_dir=dirs["aoe"], extracted_root=extracted_root)
        summary["aoes"] = len(aoes)
        all_entities.update({k: {**v, "_entity_type": "aoe"}
                             for k, v in aoes.items()})
    else:
        print(f"  [combat] WARNING: {dirs['aoe']} not found")
        summary["aoes"] = 0

    # Write combined index with ALL entity types (overwrites partial indexes
    # written by individual run_* functions above)
    combined_index = [
        {"id": v["id"], "type": v["_entity_type"]}
        for v in all_entities.values()
    ]
    Writer(extracted_root).write_index("combat", combined_index)

    print(f"[combat] Done. Summary: {summary}")
    return summary
```

- [ ] **Step 4: Run all combat tests to verify they pass**

Run: `pytest tests/domains/combat/ -v`
Expected: PASS (17 tests: 3+4+3+3+3+1)

- [ ] **Step 5: Run full test suite to verify no regressions**

Run: `pytest --tb=short -q`
Expected: All tests pass (102 → 119 tests)

- [ ] **Step 6: Commit**

```bash
git add pipeline/domains/combat/__init__.py tests/domains/combat/test_combat_integration.py
git commit -m "feat(combat): complete combat domain orchestrator + integration test"
```

---

## Chunk 2: Spells Domain

### Task 8: Scaffold Spells Domain

**Files:**
- Create: `pipeline/domains/spells/__init__.py`
- Create: `tests/domains/spells/__init__.py`

- [ ] **Step 1: Create the spells package with a stub `run()`**

```python
# pipeline/domains/spells/__init__.py
"""Spells domain extractor — run() called by extract_all.py orchestrator."""
from pathlib import Path

_V2_BASE = "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2"


def run(raw_root: Path, extracted_root: Path) -> dict:
    """Run all spells domain extractors. Returns summary of counts."""
    print("[spells] Starting extraction...")
    summary = {}
    print(f"[spells] Done. Summary: {summary}")
    return summary
```

- [ ] **Step 2: Create empty test package**

```
tests/domains/spells/__init__.py  (empty file)
```

- [ ] **Step 3: Verify import works**

Run: `pytest tests/domains/spells/ -v`
Expected: `no tests ran`

- [ ] **Step 4: Commit**

```bash
git add pipeline/domains/spells/__init__.py tests/domains/spells/__init__.py
git commit -m "feat(spells): scaffold spells domain package"
```

---

### Task 9: Extract Spells

**Files:**
- Create: `pipeline/domains/spells/extract_spells.py`
- Create: `tests/domains/spells/test_extract_spells.py`

**Raw data:** `V2/Spell/Spell/Id_Spell_*.json`
**Type:** `DCSpellDataAsset` (81 files)
**Props confirmed:** Name (FText), Desc (FText), CastingType (TagName), SourceType (TagName), CostType (TagName), Range (int), AreaRadius (int), SpellTag (TagName)

- [ ] **Step 1: Write the failing tests**

```python
# tests/domains/spells/test_extract_spells.py
"""Tests for pipeline/domains/spells/extract_spells.py"""
import json
from pathlib import Path
from pipeline.domains.spells.extract_spells import extract_spell, run_spells


def make_spell_file(tmp_path, spell_id):
    data = [{
        "Type": "DCSpellDataAsset",
        "Name": spell_id,
        "Properties": {
            "Name": {"LocalizedString": "Fireball"},
            "Desc": {"LocalizedString": "Launches a fiery projectile."},
            "CastingType": {"TagName": "Type.Casting.Normal"},
            "SourceType": {"TagName": "Source.Magic.Fire"},
            "CostType": {"TagName": "Type.Cost.Mana"},
            "Range": 800,
            "AreaRadius": 200,
            "SpellTag": {"TagName": "Spell.Fire.Fireball"},
        }
    }]
    f = tmp_path / f"{spell_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_spell_returns_id_and_fields(tmp_path):
    f = make_spell_file(tmp_path, "Id_Spell_Fireball")
    result = extract_spell(f)
    assert result is not None
    assert result["id"] == "Id_Spell_Fireball"
    assert result["name"] == "Fireball"
    assert result["casting_type"] == "Type.Casting.Normal"
    assert result["source_type"] == "Source.Magic.Fire"
    assert result["cost_type"] == "Type.Cost.Mana"
    assert result["range"] == 800
    assert result["area_radius"] == 200
    assert result["spell_tag"] == "Spell.Fire.Fireball"


def test_extract_spell_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "Other"}]', encoding="utf-8")
    assert extract_spell(f) is None


def test_run_spells_writes_entity_and_index(tmp_path):
    spell_dir = tmp_path / "spells"
    spell_dir.mkdir()
    make_spell_file(spell_dir, "Id_Spell_Fireball")
    extracted = tmp_path / "extracted"
    result = run_spells(spell_dir=spell_dir, extracted_root=extracted)
    entity = extracted / "spells" / "Id_Spell_Fireball.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["name"] == "Fireball"
    assert "_meta" in data
    index = extracted / "spells" / "_index.json"
    assert index.exists()
    assert "Id_Spell_Fireball" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/domains/spells/test_extract_spells.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `extract_spells.py`**

```python
# pipeline/domains/spells/extract_spells.py
"""Extract DCSpellDataAsset files → extracted/spells/<id>.json + _index.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_text, resolve_tag
from pipeline.core.writer import Writer


def extract_spell(file_path: Path) -> dict | None:
    """Extract one DCSpellDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCSpellDataAsset"), None)
    if not obj:
        return None

    spell_id = obj.get("Name", file_path.stem)
    props = get_properties(obj)

    return {
        "id": spell_id,
        "name": resolve_text(props.get("Name")),
        "description": resolve_text(props.get("Desc")),
        "casting_type": resolve_tag(props.get("CastingType")),
        "source_type": resolve_tag(props.get("SourceType")),
        "cost_type": resolve_tag(props.get("CostType")),
        "range": props.get("Range"),
        "area_radius": props.get("AreaRadius"),
        "spell_tag": resolve_tag(props.get("SpellTag")),
    }


def run_spells(spell_dir: Path, extracted_root: Path) -> dict:
    """Extract all Spell files → extracted/spells/<id>.json + _index.json."""
    files = find_files(str(Path(spell_dir) / "Id_Spell_*.json"))
    print(f"  [spells] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    spells = {}

    for f in files:
        result = extract_spell(f)
        if not result:
            continue
        spell_id = result["id"]
        spells[spell_id] = result
        writer.write_entity("spells", spell_id, result, source_files=[str(f)])
        index_entries.append({
            "id": spell_id,
            "name": result.get("name"),
            "source_type": result.get("source_type"),
            "spell_tag": result.get("spell_tag"),
        })

    writer.write_index("spells", index_entries)
    print(f"  [spells] Extracted {len(spells)} spells")
    return spells
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/domains/spells/test_extract_spells.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/spells/extract_spells.py tests/domains/spells/test_extract_spells.py
git commit -m "feat(spells): extract Spell domain"
```

---

### Task 10: Extract Religions

**Files:**
- Create: `pipeline/domains/spells/extract_religions.py`
- Create: `tests/domains/spells/test_extract_religions.py`

**Raw data:** `V2/Religion/Religion/Id_DesignDataReligion_*.json` (33 DCReligionDataAsset files)
**Type:** `DCReligionDataAsset`
**Note:** The V2/Religion directory contains 4 other types (DCReligionBlessingDataAsset, DCReligionOfferingRewardDataAsset, etc.) — the type filter in extract_religion() handles them naturally.
**Props confirmed from spec:** Name (FText), Desc (FText), Subtitle (FText), OfferingCost (int), Order (int)

- [ ] **Step 1: Inspect actual prop keys from a sample religion file**

Run: `cd darkanddarker-wiki && py -c "import json,pathlib; d=pathlib.Path('raw/DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/Religion/Religion'); f=sorted(d.glob('*.json'))[0]; s=json.loads(f.read_text(encoding='utf-8')); [print(o['Name'],list(o.get('Properties',{}).keys())) for o in s if isinstance(o,dict) and o.get('Type')=='DCReligionDataAsset']"`

- [ ] **Step 2: Write the failing tests**

```python
# tests/domains/spells/test_extract_religions.py
"""Tests for pipeline/domains/spells/extract_religions.py"""
import json
from pathlib import Path
from pipeline.domains.spells.extract_religions import extract_religion, run_religions


def make_religion_file(tmp_path, religion_id):
    data = [{
        "Type": "DCReligionDataAsset",
        "Name": religion_id,
        "Properties": {
            "Name": {"LocalizedString": "Blythar"},
            "Desc": {"LocalizedString": "God of chaos."},
            "Subtitle": {"LocalizedString": "The Chaotic One"},
            "OfferingCost": 50,
            "Order": 1,
        }
    }]
    f = tmp_path / f"{religion_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_religion_returns_id_and_fields(tmp_path):
    f = make_religion_file(tmp_path, "Id_DesignDataReligion_Blythar")
    result = extract_religion(f)
    assert result is not None
    assert result["id"] == "Id_DesignDataReligion_Blythar"
    assert result["name"] == "Blythar"
    assert result["description"] == "God of chaos."
    assert result["subtitle"] == "The Chaotic One"
    assert result["offering_cost"] == 50
    assert result["order"] == 1


def test_extract_religion_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCReligionBlessingDataAsset"}]', encoding="utf-8")
    assert extract_religion(f) is None


def test_run_religions_writes_entity_and_index(tmp_path):
    religion_dir = tmp_path / "religions"
    religion_dir.mkdir()
    make_religion_file(religion_dir, "Id_DesignDataReligion_Blythar")
    extracted = tmp_path / "extracted"
    result = run_religions(religion_dir=religion_dir, extracted_root=extracted)
    entity = extracted / "spells" / "Id_DesignDataReligion_Blythar.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["name"] == "Blythar"
    assert "_meta" in data
    index = extracted / "spells" / "_index.json"
    assert index.exists()
    assert "Id_DesignDataReligion_Blythar" in result
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/domains/spells/test_extract_religions.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implement `extract_religions.py`**

```python
# pipeline/domains/spells/extract_religions.py
"""Extract DCReligionDataAsset files → extracted/spells/<id>.json + _index.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_text
from pipeline.core.writer import Writer


def extract_religion(file_path: Path) -> dict | None:
    """Extract one DCReligionDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCReligionDataAsset"), None)
    if not obj:
        return None

    religion_id = obj.get("Name", file_path.stem)
    props = get_properties(obj)

    return {
        "id": religion_id,
        "name": resolve_text(props.get("Name")),
        "description": resolve_text(props.get("Desc")),
        "subtitle": resolve_text(props.get("Subtitle")),
        "offering_cost": props.get("OfferingCost"),
        "order": props.get("Order"),
    }


def run_religions(religion_dir: Path, extracted_root: Path) -> dict:
    """Extract all Religion files → extracted/spells/<id>.json + _index.json.

    NOTE: religion_dir should point to V2/Religion/Religion/ (base type only).
    The parent V2/Religion/ directory contains 4 other types which are out of scope.
    """
    files = find_files(str(Path(religion_dir) / "*.json"))
    print(f"  [religions] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    religions = {}

    for f in files:
        result = extract_religion(f)
        if not result:
            continue
        religion_id = result["id"]
        religions[religion_id] = result
        writer.write_entity("spells", religion_id, result, source_files=[str(f)])
        index_entries.append({
            "id": religion_id,
            "name": result.get("name"),
            "order": result.get("order"),
        })

    writer.write_index("spells", index_entries)
    print(f"  [religions] Extracted {len(religions)} religions")
    return religions
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/domains/spells/test_extract_religions.py -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add pipeline/domains/spells/extract_religions.py tests/domains/spells/test_extract_religions.py
git commit -m "feat(spells): extract Religion domain"
```

---

### Task 11: Extract Faustian Bargains

**Files:**
- Create: `pipeline/domains/spells/extract_faustian_bargains.py`
- Create: `tests/domains/spells/test_extract_faustian_bargains.py`

**Raw data:** `V2/FaustianBargain/FaustianBargain/Id_FaustianBargain_*.json`
**Type:** `DCFaustianBargainDataAsset` (156 files)
**Props confirmed:** MonsterId (AssetPathName dict), RequiredAffinity (int), Skills (list of asset refs), Abilities (list of asset refs), Effects (list of asset refs)
**MonsterId resolution:** Same pattern as item properties — `path.split("/")[-1].split(".")[0]` from the AssetPathName string (e.g. `/Game/.../Id_Monster_Foo.Id_Monster_Foo` → `Id_Monster_Foo`)

- [ ] **Step 1: Write the failing tests**

```python
# tests/domains/spells/test_extract_faustian_bargains.py
"""Tests for pipeline/domains/spells/extract_faustian_bargains.py"""
import json
from pathlib import Path
from pipeline.domains.spells.extract_faustian_bargains import (
    extract_faustian_bargain, run_faustian_bargains
)


def make_fb_file(tmp_path, fb_id):
    data = [{
        "Type": "DCFaustianBargainDataAsset",
        "Name": fb_id,
        "Properties": {
            "MonsterId": {
                "AssetPathName": "/Game/.../Id_Monster_Lich.Id_Monster_Lich",
                "SubPathString": ""
            },
            "RequiredAffinity": 3,
            "Skills": [
                {"AssetPathName": "/Game/.../Id_Skill_DeathGaze.Id_Skill_DeathGaze", "SubPathString": ""}
            ],
            "Abilities": [],
            "Effects": [],
        }
    }]
    f = tmp_path / f"{fb_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_faustian_bargain_returns_id_and_fields(tmp_path):
    f = make_fb_file(tmp_path, "Id_FaustianBargain_Lich")
    result = extract_faustian_bargain(f)
    assert result is not None
    assert result["id"] == "Id_FaustianBargain_Lich"
    assert result["monster_id"] == "Id_Monster_Lich"
    assert result["required_affinity"] == 3
    assert "Id_Skill_DeathGaze" in result["skills"]


def test_extract_faustian_bargain_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "Other"}]', encoding="utf-8")
    assert extract_faustian_bargain(f) is None


def test_run_faustian_bargains_writes_entity_and_index(tmp_path):
    fb_dir = tmp_path / "fb"
    fb_dir.mkdir()
    make_fb_file(fb_dir, "Id_FaustianBargain_Lich")
    extracted = tmp_path / "extracted"
    result = run_faustian_bargains(fb_dir=fb_dir, extracted_root=extracted)
    entity = extracted / "spells" / "Id_FaustianBargain_Lich.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["monster_id"] == "Id_Monster_Lich"
    assert "_meta" in data
    index = extracted / "spells" / "_index.json"
    assert index.exists()
    assert "Id_FaustianBargain_Lich" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/domains/spells/test_extract_faustian_bargains.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `extract_faustian_bargains.py`**

```python
# pipeline/domains/spells/extract_faustian_bargains.py
"""Extract DCFaustianBargainDataAsset → extracted/spells/<id>.json + _index.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.writer import Writer


def _resolve_asset_path_name(value: dict | None) -> str | None:
    """Resolve {AssetPathName: '/Game/.../Id_Foo.Id_Foo'} → 'Id_Foo'."""
    if not isinstance(value, dict):
        return None
    path = value.get("AssetPathName", "")
    if not path or path == "None":
        return None
    return path.split("/")[-1].split(".")[0]


def _resolve_asset_list(items: list) -> list[str]:
    """Resolve a list of AssetPathName dicts → list of ID strings."""
    result = []
    for item in (items or []):
        resolved = _resolve_asset_path_name(item)
        if resolved:
            result.append(resolved)
    return result


def extract_faustian_bargain(file_path: Path) -> dict | None:
    """Extract one DCFaustianBargainDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCFaustianBargainDataAsset"), None)
    if not obj:
        return None

    fb_id = obj.get("Name", file_path.stem)
    props = get_properties(obj)

    return {
        "id": fb_id,
        "monster_id": _resolve_asset_path_name(props.get("MonsterId")),
        "required_affinity": props.get("RequiredAffinity"),
        "skills": _resolve_asset_list(props.get("Skills")),
        "abilities": _resolve_asset_list(props.get("Abilities")),
        "effects": _resolve_asset_list(props.get("Effects")),
    }


def run_faustian_bargains(fb_dir: Path, extracted_root: Path) -> dict:
    """Extract all FaustianBargain files → extracted/spells/<id>.json + _index.json."""
    files = find_files(str(Path(fb_dir) / "Id_FaustianBargain_*.json"))
    print(f"  [faustian_bargains] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    bargains = {}

    for f in files:
        result = extract_faustian_bargain(f)
        if not result:
            continue
        fb_id = result["id"]
        bargains[fb_id] = result
        writer.write_entity("spells", fb_id, result, source_files=[str(f)])
        index_entries.append({
            "id": fb_id,
            "monster_id": result.get("monster_id"),
            "required_affinity": result.get("required_affinity"),
        })

    writer.write_index("spells", index_entries)
    print(f"  [faustian_bargains] Extracted {len(bargains)} Faustian bargains")
    return bargains
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/domains/spells/test_extract_faustian_bargains.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/spells/extract_faustian_bargains.py tests/domains/spells/test_extract_faustian_bargains.py
git commit -m "feat(spells): extract FaustianBargain domain"
```

---

### Task 12: Spells Orchestrator + Integration Test

**Files:**
- Modify: `pipeline/domains/spells/__init__.py`
- Create: `tests/domains/spells/test_spells_integration.py`

**Integration test reads real data from:** `raw/DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/Spell/Spell/`

- [ ] **Step 1: Write the failing integration test**

```python
# tests/domains/spells/test_spells_integration.py
"""Integration test: run spells domain against real raw data."""
from pathlib import Path
import pytest
from pipeline.domains.spells import run

RAW_ROOT = Path("raw")
SPELL_DIR = RAW_ROOT / "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/Spell/Spell"


@pytest.mark.skipif(not SPELL_DIR.exists(), reason="raw data not present")
def test_spells_run_integration(tmp_path):
    summary = run(raw_root=RAW_ROOT, extracted_root=tmp_path)
    assert summary.get("spells", 0) > 50
    assert summary.get("religions", 0) > 10
    assert summary.get("faustian_bargains", 0) > 50
    index = tmp_path / "spells" / "_index.json"
    assert index.exists()
    import json
    index_data = json.loads(index.read_text(encoding="utf-8"))
    entity_types = {e["type"] for e in index_data["entries"]}
    assert "spell" in entity_types
    assert "religion" in entity_types
    assert "faustian_bargain" in entity_types
```

- [ ] **Step 2: Run integration test to see current failure**

Run: `pytest tests/domains/spells/test_spells_integration.py -v`
Expected: FAIL

- [ ] **Step 3: Implement the spells orchestrator**

```python
# pipeline/domains/spells/__init__.py
"""Spells domain extractor — run() called by extract_all.py orchestrator."""
from pathlib import Path

from pipeline.domains.spells.extract_spells import run_spells
from pipeline.domains.spells.extract_religions import run_religions
from pipeline.domains.spells.extract_faustian_bargains import run_faustian_bargains
from pipeline.core.writer import Writer

_V2_BASE = "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2"


def run(raw_root: Path, extracted_root: Path) -> dict:
    """Run all spells domain extractors. Returns summary of counts.

    NOTE: Individual run_* functions each write a partial _index.json as a
    side-effect (useful for standalone runs / unit tests). This orchestrator
    overwrites that partial index with a single combined index containing all
    entity types at the end.
    """
    print("[spells] Starting extraction...")
    summary = {}
    all_entities: dict[str, dict] = {}

    dirs = {
        "spell": raw_root / _V2_BASE / "Spell" / "Spell",
        "religion": raw_root / _V2_BASE / "Religion" / "Religion",
        "fb": raw_root / _V2_BASE / "FaustianBargain" / "FaustianBargain",
    }

    if dirs["spell"].exists():
        spells = run_spells(spell_dir=dirs["spell"], extracted_root=extracted_root)
        summary["spells"] = len(spells)
        all_entities.update({k: {**v, "_entity_type": "spell"}
                             for k, v in spells.items()})
    else:
        print(f"  [spells] WARNING: {dirs['spell']} not found")
        summary["spells"] = 0

    if dirs["religion"].exists():
        religions = run_religions(religion_dir=dirs["religion"], extracted_root=extracted_root)
        summary["religions"] = len(religions)
        all_entities.update({k: {**v, "_entity_type": "religion"}
                             for k, v in religions.items()})
    else:
        print(f"  [spells] WARNING: {dirs['religion']} not found")
        summary["religions"] = 0

    if dirs["fb"].exists():
        fbs = run_faustian_bargains(fb_dir=dirs["fb"], extracted_root=extracted_root)
        summary["faustian_bargains"] = len(fbs)
        all_entities.update({k: {**v, "_entity_type": "faustian_bargain"}
                             for k, v in fbs.items()})
    else:
        print(f"  [spells] WARNING: {dirs['fb']} not found")
        summary["faustian_bargains"] = 0

    # Write combined index with ALL entity types (overwrites partial indexes
    # written by individual run_* functions above)
    combined_index = [
        {"id": v["id"], "name": v.get("name"), "type": v["_entity_type"]}
        for v in all_entities.values()
    ]
    Writer(extracted_root).write_index("spells", combined_index)

    print(f"[spells] Done. Summary: {summary}")
    return summary
```

- [ ] **Step 4: Run all spells tests to verify they pass**

Run: `pytest tests/domains/spells/ -v`
Expected: PASS (10 tests: 3+3+3+1)

- [ ] **Step 5: Run full test suite to verify no regressions**

Run: `pytest --tb=short -q`
Expected: All tests pass (119 → 129 tests)

- [ ] **Step 6: Commit**

```bash
git add pipeline/domains/spells/__init__.py tests/domains/spells/test_spells_integration.py
git commit -m "feat(spells): complete spells domain orchestrator + integration test"
```

---

## Chunk 3: Status Domain

### Task 13: Scaffold Status Domain

**Files:**
- Create: `pipeline/domains/status/__init__.py`
- Create: `tests/domains/status/__init__.py`

- [ ] **Step 1: Create the status package with a stub `run()`**

```python
# pipeline/domains/status/__init__.py
"""Status domain extractor — run() called by extract_all.py orchestrator."""
from pathlib import Path

_V2_BASE = "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2"


def run(raw_root: Path, extracted_root: Path) -> dict:
    """Run all status domain extractors. Returns summary of counts."""
    print("[status] Starting extraction...")
    summary = {}
    print(f"[status] Done. Summary: {summary}")
    return summary
```

- [ ] **Step 2: Create empty test package**

```
tests/domains/status/__init__.py  (empty file)
```

- [ ] **Step 3: Verify import works**

Run: `pytest tests/domains/status/ -v`
Expected: `no tests ran`

- [ ] **Step 4: Commit**

```bash
git add pipeline/domains/status/__init__.py tests/domains/status/__init__.py
git commit -m "feat(status): scaffold status domain package"
```

---

### Task 14: Extract Status Effects (Unified Extractor)

**Files:**
- Create: `pipeline/domains/status/extract_status_effects.py`
- Create: `tests/domains/status/test_extract_status_effects.py`

**All 4 status subtypes share `DCGameplayEffectDataAsset`.** A single extractor handles all 4, distinguished by a `category` parameter.

**Category → V2 directory mapping:**
- `"player"` → `V2/ActorStatus/StatusEffect/` (810 files)
- `"monster"` → `V2/ActorStatusMonster/StatusEffect/` (158 files)
- `"in_water"` → `V2/ActorStatusInWater/StatusEffect/` (9 files)
- `"item_cosmetic"` → `V2/ActorStatusItemCosmetic/StatusEffect/` (30 files)

**Props common across categories:** EventTag (TagName), AssetTags (list of {TagName}), Duration (float/int, when present)
**Category-specific props:** TargetType (TagName, present in monster/in_water), ExecOxygen (in_water), StrengthBase (item_cosmetic)

- [ ] **Step 1: Write the failing tests**

```python
# tests/domains/status/test_extract_status_effects.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/domains/status/test_extract_status_effects.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement `extract_status_effects.py`**

```python
# pipeline/domains/status/extract_status_effects.py
"""Extract DCGameplayEffectDataAsset files → extracted/status/<id>.json + _index.json.

All 4 status subtypes (player, monster, in_water, item_cosmetic) share this extractor.
The 'category' parameter identifies which subtype is being processed.
"""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_tag
from pipeline.core.writer import Writer


def extract_status_effect(file_path: Path, category: str) -> dict | None:
    """Extract one DCGameplayEffectDataAsset file with the given category label."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCGameplayEffectDataAsset"), None)
    if not obj:
        return None

    status_id = obj.get("Name", file_path.stem)
    props = get_properties(obj)

    asset_tags = [
        resolve_tag(t) for t in (props.get("AssetTags") or [])
        if resolve_tag(t) is not None
    ]

    return {
        "id": status_id,
        "category": category,
        "event_tag": resolve_tag(props.get("EventTag")),
        "asset_tags": asset_tags,
        "duration": props.get("Duration"),
        "target_type": resolve_tag(props.get("TargetType")),
    }


def run_status_effects(status_dir: Path, category: str, extracted_root: Path) -> dict:
    """Extract all status effect files → extracted/status/<id>.json + _index.json."""
    files = find_files(str(Path(status_dir) / "*.json"))
    print(f"  [status/{category}] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    effects = {}

    for f in files:
        result = extract_status_effect(f, category=category)
        if not result:
            continue
        status_id = result["id"]
        effects[status_id] = result
        writer.write_entity("status", status_id, result, source_files=[str(f)])
        index_entries.append({
            "id": status_id,
            "category": category,
            "event_tag": result.get("event_tag"),
            "asset_tags": result.get("asset_tags"),
        })

    writer.write_index("status", index_entries)
    print(f"  [status/{category}] Extracted {len(effects)} status effects")
    return effects
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/domains/status/test_extract_status_effects.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/status/extract_status_effects.py tests/domains/status/test_extract_status_effects.py
git commit -m "feat(status): unified status effect extractor with category parameter"
```

---

### Task 15: Status Orchestrator + Combined Index + Integration Test

**Files:**
- Modify: `pipeline/domains/status/__init__.py`
- Create: `tests/domains/status/test_status_integration.py`

**Combined-index pattern:** Same as classes domain. Each `run_status_effects()` call writes a partial `_index.json`. The orchestrator accumulates all results and overwrites with a combined index containing all 4 categories. This mirrors `pipeline/domains/classes/__init__.py`.

**Integration test reads real data from:** `raw/DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/ActorStatus/StatusEffect/`

- [ ] **Step 1: Write the failing integration test**

```python
# tests/domains/status/test_status_integration.py
"""Integration test: run status domain against real raw data."""
import json
from pathlib import Path
import pytest
from pipeline.domains.status import run

RAW_ROOT = Path("raw")
ACTOR_STATUS_DIR = RAW_ROOT / "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/ActorStatus/StatusEffect"


@pytest.mark.skipif(not ACTOR_STATUS_DIR.exists(), reason="raw data not present")
def test_status_run_integration(tmp_path):
    summary = run(raw_root=RAW_ROOT, extracted_root=tmp_path)
    assert summary.get("player", 0) > 500
    assert summary.get("monster", 0) > 100
    assert summary.get("in_water", 0) > 0
    assert summary.get("item_cosmetic", 0) > 0
    index = tmp_path / "status" / "_index.json"
    assert index.exists()
    data = json.loads(index.read_text(encoding="utf-8"))
    # Combined index should have entries from all 4 categories
    categories = {e["category"] for e in data["entries"]}
    assert "player" in categories
    assert "monster" in categories
```

- [ ] **Step 2: Run integration test to see current failure**

Run: `pytest tests/domains/status/test_status_integration.py -v`
Expected: FAIL — stub run() returns empty summary

- [ ] **Step 3: Implement the status orchestrator with combined-index**

```python
# pipeline/domains/status/__init__.py
"""Status domain extractor — run() called by extract_all.py orchestrator."""
from pathlib import Path

from pipeline.domains.status.extract_status_effects import run_status_effects
from pipeline.core.writer import Writer

_V2_BASE = "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2"


def run(raw_root: Path, extracted_root: Path) -> dict:
    """Run all status domain extractors. Returns summary of counts per category.

    NOTE: run_status_effects() writes a partial _index.json on each call.
    This orchestrator overwrites that with a combined index covering all
    4 categories, using the same combined-index pattern as the classes domain.
    """
    print("[status] Starting extraction...")
    summary = {}
    all_effects: dict[str, dict] = {}

    dirs = {
        "player": raw_root / _V2_BASE / "ActorStatus" / "StatusEffect",
        "monster": raw_root / _V2_BASE / "ActorStatusMonster" / "StatusEffect",
        "in_water": raw_root / _V2_BASE / "ActorStatusInWater" / "StatusEffect",
        "item_cosmetic": raw_root / _V2_BASE / "ActorStatusItemCosmetic" / "StatusEffect",
    }

    for category, status_dir in dirs.items():
        if status_dir.exists():
            effects = run_status_effects(
                status_dir=status_dir, category=category, extracted_root=extracted_root
            )
            summary[category] = len(effects)
            all_effects.update(effects)
        else:
            print(f"  [status] WARNING: {status_dir} not found")
            summary[category] = 0

    # Write combined index with ALL categories (overwrites partial indexes
    # written by individual run_status_effects calls above)
    combined_index = [
        {
            "id": v["id"],
            "category": v["category"],
            "event_tag": v.get("event_tag"),
            "asset_tags": v.get("asset_tags"),
        }
        for v in all_effects.values()
    ]
    Writer(extracted_root).write_index("status", combined_index)

    print(f"[status] Done. Summary: {summary}")
    return summary
```

- [ ] **Step 4: Run all status tests to verify they pass**

Run: `pytest tests/domains/status/ -v`
Expected: PASS (5 tests: 4+1)

- [ ] **Step 5: Run full test suite to verify no regressions**

Run: `pytest --tb=short -q`
Expected: All tests pass (129 → 134 tests)

- [ ] **Step 6: Commit**

```bash
git add pipeline/domains/status/__init__.py tests/domains/status/test_status_integration.py
git commit -m "feat(status): complete status domain orchestrator with combined-index"
```
