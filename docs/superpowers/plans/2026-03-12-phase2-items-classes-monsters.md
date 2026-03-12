# Phase 2: Items, Classes, and Monsters Domain Extractors Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build domain extractors for `items` (Item + ItemProperty), `classes` (PlayerCharacter + Perk + Skill + ShapeShift), and `monsters` (Monster) producing wiki-ready entity JSON files and indexes.

**Architecture:** Three domain packages each expose a `run()` function. The items domain builds an ItemPropertyType catalog and ItemProperty lookup first, then merges properties into each item entity file. Classes and monsters domains write per-entity JSON + domain index files. All extractors use `pipeline.core.*` exclusively; no direct stdlib I/O.

**Tech Stack:** Python 3.10+, pytest, pathlib, pipeline.core (reader, normalizer, writer)

---

## Confirmed Raw Data Structures (from exploration)

| System | UE5 Type | Directory | Files | Properties container |
|---|---|---|---|---|
| Item | `DCItemDataAsset` | `V2/Item/Item/` | 2,373 | Direct at `Properties` |
| ItemPropertyType | `DCItemPropertyTypeDataAsset` | `V2/ItemProperty/ItemPropertyType/` | 65 | Direct at `Properties` |
| ItemProperty | `DCItemPropertyDataAsset` | `V2/ItemProperty/ItemProperty/` | 1,753 | `Properties.ItemPropertyItemArray` |
| PlayerCharacterEffect | `DCGameplayEffectDataAsset` | `V2/PlayerCharacter/PlayerCharacterEffect/` | 44 | Direct at `Properties` |
| Perk | `DCPerkDataAsset` | `V2/Perk/Perk/` | 133 | Direct at `Properties` |
| Skill | `DCSkillDataAsset` | `V2/Skill/Skill/` | 68 | Direct at `Properties` |
| ShapeShift | `DCShapeShiftDataAsset` | `V2/ShapeShift/ShapeShift/` | 7 | Direct at `Properties` |
| Monster | `DCMonsterDataAsset` | `V2/Monster/Monster/` | 392 | Direct at `Properties` |

**Key patterns (all identical to Phase 1):**
- `get_properties(obj)` → the `Properties` dict (no `Properties.Item` wrapper in any of these systems)
- `resolve_text(props.get("Name"))` → extracts `LocalizedString` from FText structs
- `resolve_tag(props.get("SlotType"))` → extracts `TagName` string from tag structs
- `resolve_ref(props.get("SomeRef"))` → extracts asset path string from `{ObjectName, ObjectPath}` structs
- Type strings are **DC-prefixed** (e.g., `DCItemDataAsset` NOT `Item`)

---

## File Map

**Create (items domain):**
- `pipeline/domains/items/__init__.py`
- `pipeline/domains/items/extract_item_properties.py`
- `pipeline/domains/items/extract_items.py`
- `tests/domains/items/__init__.py`
- `tests/domains/items/test_extract_item_properties.py`
- `tests/domains/items/test_extract_items.py`
- `tests/domains/items/test_items_run.py`

**Create (classes domain):**
- `pipeline/domains/classes/__init__.py`
- `pipeline/domains/classes/extract_player_characters.py`
- `pipeline/domains/classes/extract_perks.py`
- `pipeline/domains/classes/extract_skills.py`
- `pipeline/domains/classes/extract_shapeshifts.py`
- `tests/domains/classes/__init__.py`
- `tests/domains/classes/test_extract_player_characters.py`
- `tests/domains/classes/test_extract_perks.py`
- `tests/domains/classes/test_extract_skills.py`
- `tests/domains/classes/test_extract_shapeshifts.py`
- `tests/domains/classes/test_classes_run.py`

**Create (monsters domain):**
- `pipeline/domains/monsters/__init__.py`
- `pipeline/domains/monsters/extract_monsters.py`
- `tests/domains/monsters/__init__.py`
- `tests/domains/monsters/test_extract_monsters.py`
- `tests/domains/monsters/test_monsters_run.py`

---

## Chunk 1: Items Domain

### Task 1: Items domain scaffold

**Files:**
- Create: `pipeline/domains/items/__init__.py` (empty)
- Create: `tests/domains/items/__init__.py` (empty)

- [ ] **Step 1: Create empty init files**

```bash
mkdir -p pipeline/domains/items tests/domains/items
touch pipeline/domains/items/__init__.py tests/domains/items/__init__.py
```

- [ ] **Step 2: Verify pytest can discover the new package**

```bash
py -3 -m pytest tests/domains/items/ -v
```
Expected: `no tests ran` (0 collected) — not a failure

---

### Task 2: extract_item_properties.py

**Files:**
- Create: `pipeline/domains/items/extract_item_properties.py`
- Create: `tests/domains/items/test_extract_item_properties.py`

Background: Two asset types live in the ItemProperty directory:
1. `DCItemPropertyTypeDataAsset` — defines what a property type IS (65 files). Output: `extracted/items/item_property_types.json`.
2. `DCItemPropertyDataAsset` — lists the actual stat values for each item variant (1,753 files). Not written separately; instead, `build_property_lookup()` returns an in-memory dict used by `extract_items.py` to merge properties into each item entity.

**Linking strategy:** `Id_ItemProperty_Primary_AdventurerBoots_1001.json` → item id `Id_Item_AdventurerBoots_1001`. Strip the prefix (`Id_ItemProperty_Primary_`, `Id_ItemProperty_Secondary_`, or `Id_ItemProperty_`) and prepend `Id_Item_`.

- [ ] **Step 1: Explore a sample ItemPropertyType and ItemProperty file to confirm field names**

```bash
py -3 -c "
import json
from pathlib import Path

# ItemPropertyType
f = sorted(Path('raw/DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/ItemProperty/ItemPropertyType').glob('*.json'))[0]
d = json.loads(f.read_text(encoding='utf-8'))[0]
print('ItemPropertyType keys:', list(d.get('Properties', {}).keys()))

# ItemProperty
f2 = sorted(Path('raw/DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/ItemProperty/ItemProperty').glob('*.json'))[0]
d2 = json.loads(f2.read_text(encoding='utf-8'))[0]
arr = d2.get('Properties', {}).get('ItemPropertyItemArray', [])
print('ItemProperty array entry keys:', list(arr[0].keys()) if arr else 'empty')
if arr:
    print('PropertyTypeId sample:', arr[0].get('PropertyTypeId'))
"
```
Expected: shows `PropertyTypeGroupId`, `PropertyType`, `ValueRatio`, `EnchantItemIdTag` for ItemPropertyType; shows `PropertyTypeId`, `MinValue`, `MaxValue`, `EnchantMinValue`, `EnchantMaxValue` for ItemProperty array entries.

- [ ] **Step 2: Write the failing tests**

`tests/domains/items/test_extract_item_properties.py`:
```python
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
```

- [ ] **Step 3: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/items/test_extract_item_properties.py -v
```
Expected: `ImportError`

- [ ] **Step 4: Implement pipeline/domains/items/extract_item_properties.py**

```python
"""Extract ItemPropertyType catalog and ItemProperty instance lookup.

extract_item_property_type(): parses one DCItemPropertyTypeDataAsset file.
build_property_lookup(): returns {item_id: [entries]} from all ItemProperty files.
run_item_property_types(): writes extracted/items/item_property_types.json.
"""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_tag, resolve_ref
from pipeline.core.writer import Writer


def extract_item_property_type(file_path: Path) -> dict | None:
    """Extract one DCItemPropertyTypeDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCItemPropertyTypeDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    return {
        "id": obj.get("Name", file_path.stem),
        "property_type": resolve_tag(props.get("PropertyType")),
        "value_ratio": props.get("ValueRatio", 1.0),
        "enchant_item_id": resolve_tag(props.get("EnchantItemIdTag")),
        "source_file": str(file_path),
    }


def _resolve_property_type_id(value) -> str | None:
    """Resolve PropertyTypeId — may be a tag or an asset ref."""
    if value is None:
        return None
    tag = resolve_tag(value)
    if tag is not None:
        return tag
    return resolve_ref(value)


def build_property_lookup(property_dir: Path) -> dict:
    """Build {item_id: [property_entries]} from ItemProperty files.

    Links Id_ItemProperty_Primary_<Suffix> → Id_Item_<Suffix>.
    Does NOT write any output files.
    """
    lookup: dict[str, list] = {}
    prefixes = ("Id_ItemProperty_Primary_", "Id_ItemProperty_Secondary_", "Id_ItemProperty_")

    for f in find_files(str(Path(property_dir) / "Id_ItemProperty_*.json")):
        try:
            data = load(f)
        except (FileNotFoundError, ValueError):
            continue

        obj = next((o for o in data if isinstance(o, dict)
                    and o.get("Type") == "DCItemPropertyDataAsset"), None)
        if not obj:
            continue

        # Derive item_id from file stem
        stem = f.stem
        item_id = None
        for prefix in prefixes:
            if stem.startswith(prefix):
                item_id = "Id_Item_" + stem[len(prefix):]
                break
        if not item_id:
            continue

        props = get_properties(obj)
        entries = []
        for entry in (props.get("ItemPropertyItemArray") or []):
            entries.append({
                "property_type": _resolve_property_type_id(entry.get("PropertyTypeId")),
                "min_value": entry.get("MinValue"),
                "max_value": entry.get("MaxValue"),
                "enchant_min_value": entry.get("EnchantMinValue"),
                "enchant_max_value": entry.get("EnchantMaxValue"),
            })

        if entries:
            lookup.setdefault(item_id, []).extend(entries)

    return lookup


def run_item_property_types(type_dir: Path, extracted_root: Path) -> dict:
    """Extract all ItemPropertyType files → extracted/items/item_property_types.json."""
    files = find_files(str(Path(type_dir) / "Id_ItemPropertyType_*.json"))
    print(f"  [item_property_types] Found {len(files)} files")

    types = {}
    source_files = []
    for f in files:
        result = extract_item_property_type(f)
        if result:
            types[result["id"]] = {
                "property_type": result["property_type"],
                "value_ratio": result["value_ratio"],
                "enchant_item_id": result["enchant_item_id"],
            }
            source_files.append(result["source_file"])

    writer = Writer(extracted_root)
    writer.write_system("items", "item_property_types", {"types": types},
                        source_files=source_files)
    print(f"  [item_property_types] Extracted {len(types)} property types")
    return types
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/items/test_extract_item_properties.py -v
```
Expected: all 4 tests PASS

- [ ] **Step 6: Run full suite to check nothing broke**

```bash
py -3 -m pytest --tb=short -q
```
Expected: 80 total tests passing (76 + 4 new)

---

### Task 3: extract_items.py

**Files:**
- Create: `pipeline/domains/items/extract_items.py`
- Create: `tests/domains/items/test_extract_items.py`

Background: 2,373 `DCItemDataAsset` files in `V2/Item/Item/`. Each becomes an entity file at `extracted/items/<id>.json`. Properties (from `build_property_lookup`) are merged in if available. A domain index is written at `extracted/items/_index.json`.

- [ ] **Step 1: Explore a sample Item file to confirm all important field names**

```bash
py -3 -c "
import json
from pathlib import Path
f = sorted(Path('raw/DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/Item/Item').glob('*.json'))[0]
d = json.loads(f.read_text(encoding='utf-8'))[0]
props = d.get('Properties', {})
print('Name:', d.get('Name'))
print('Type:', d.get('Type'))
print('Props keys:', list(props.keys())[:15])
for k in ('Name', 'FlavorText', 'ItemType', 'SlotType', 'RarityType', 'MaxCount', 'CanDrop'):
    print(f'  {k}:', repr(props.get(k))[:80])
"
```
Expected: confirms field names match the table above.

- [ ] **Step 2: Write the failing tests**

`tests/domains/items/test_extract_items.py`:
```python
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
```

- [ ] **Step 3: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/items/test_extract_items.py -v
```
Expected: `ImportError`

- [ ] **Step 4: Implement pipeline/domains/items/extract_items.py**

```python
"""Extract DCItemDataAsset files → extracted/items/<id>.json + _index.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_text, resolve_tag
from pipeline.core.writer import Writer


def extract_item(file_path: Path, property_lookup: dict | None = None) -> dict | None:
    """Extract one DCItemDataAsset file into a normalized dict."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCItemDataAsset"), None)
    if not obj:
        return None

    item_id = obj.get("Name", file_path.stem)
    props = get_properties(obj)

    # Strip EItemType:: prefix (e.g. "EItemType::Armor" → "Armor")
    raw_item_type = props.get("ItemType", "")
    item_type = raw_item_type.split("::")[-1] if "::" in raw_item_type else raw_item_type

    result: dict = {
        "id": item_id,
        "name": resolve_text(props.get("Name")),
        "flavor_text": resolve_text(props.get("FlavorText")),
        "item_type": item_type,
        "slot_type": resolve_tag(props.get("SlotType")),
        "armor_type": resolve_tag(props.get("ArmorType")),
        "rarity_type": resolve_tag(props.get("RarityType")),
        "max_count": props.get("MaxCount", 1),
        "can_drop": props.get("CanDrop", True),
        "inventory_width": props.get("InventoryWidth", 1),
        "inventory_height": props.get("InventoryHeight", 1),
    }

    if property_lookup and item_id in property_lookup:
        result["properties"] = property_lookup[item_id]

    return result


def run_items(item_dir: Path, extracted_root: Path,
              property_lookup: dict | None = None) -> dict:
    """Extract all Item files → extracted/items/<id>.json + _index.json."""
    files = find_files(str(Path(item_dir) / "Id_Item_*.json"))
    print(f"  [items] Found {len(files)} item files")

    writer = Writer(extracted_root)
    index_entries = []
    items = {}

    for f in files:
        result = extract_item(f, property_lookup)
        if not result:
            continue
        item_id = result["id"]
        items[item_id] = result
        writer.write_entity("items", item_id, result, source_files=[str(f)])
        index_entries.append({
            "id": item_id,
            "name": result.get("name"),
            "item_type": result.get("item_type"),
            "slot_type": result.get("slot_type"),
            "rarity_type": result.get("rarity_type"),
        })

    writer.write_index("items", index_entries)
    print(f"  [items] Extracted {len(items)} items")
    return items
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/items/test_extract_items.py -v
```
Expected: all 4 tests PASS

- [ ] **Step 6: Run full suite**

```bash
py -3 -m pytest --tb=short -q
```
Expected: 84 total tests passing

---

### Task 4: items domain __init__.py + smoke test

**Files:**
- Modify: `pipeline/domains/items/__init__.py`
- Create: `tests/domains/items/test_items_run.py`

- [ ] **Step 1: Implement run()**

`pipeline/domains/items/__init__.py`:
```python
"""Items domain extractor — run() called by extract_all.py orchestrator."""
from pathlib import Path

from pipeline.domains.items.extract_item_properties import (
    run_item_property_types,
    build_property_lookup,
)
from pipeline.domains.items.extract_items import run_items

_V2_BASE = "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2"


def run(raw_root: Path, extracted_root: Path) -> dict:
    """Run all items domain extractors. Returns summary of counts."""
    print("[items] Starting extraction...")
    summary = {}

    type_dir = raw_root / _V2_BASE / "ItemProperty" / "ItemPropertyType"
    property_dir = raw_root / _V2_BASE / "ItemProperty" / "ItemProperty"
    item_dir = raw_root / _V2_BASE / "Item" / "Item"

    # 1. Extract property type catalog
    if type_dir.exists():
        property_types = run_item_property_types(type_dir=type_dir, extracted_root=extracted_root)
        summary["item_property_types"] = len(property_types)
    else:
        print(f"  [items] WARNING: {type_dir} not found, skipping property types")
        summary["item_property_types"] = 0

    # 2. Build in-memory property lookup (used to merge into item entity files)
    property_lookup = {}
    if property_dir.exists():
        property_lookup = build_property_lookup(property_dir)
        print(f"  [items] Built property lookup: {len(property_lookup)} items with properties")
    else:
        print(f"  [items] WARNING: {property_dir} not found, items will have no properties")

    # 3. Extract items with merged properties
    if item_dir.exists():
        items = run_items(item_dir=item_dir, extracted_root=extracted_root,
                         property_lookup=property_lookup)
        summary["items"] = len(items)
    else:
        print(f"  [items] WARNING: {item_dir} not found, skipping items")
        summary["items"] = 0

    summary["items_with_properties"] = len(property_lookup)
    print(f"[items] Done. Summary: {summary}")
    return summary
```

- [ ] **Step 2: Write smoke test**

`tests/domains/items/test_items_run.py`:
```python
"""Smoke test for items domain run() function."""
import json
from pathlib import Path
from pipeline.domains.items import run


def test_items_run_smoke(tmp_path):
    """run() completes without error on empty raw dirs."""
    raw = tmp_path / "raw"
    raw.mkdir()
    extracted = tmp_path / "extracted"
    summary = run(raw_root=raw, extracted_root=extracted)
    assert isinstance(summary, dict)
    required_keys = ("items", "items_with_properties", "item_property_types")
    assert all(k in summary for k in required_keys)
    assert all(isinstance(summary[k], int) for k in required_keys)
```

- [ ] **Step 3: Run smoke test**

```bash
py -3 -m pytest tests/domains/items/test_items_run.py -v
```
Expected: PASS

- [ ] **Step 4: Run full suite**

```bash
py -3 -m pytest --tb=short -q
```
Expected: 85 total tests passing

---

## Chunk 2: Classes Domain

### Task 5: Classes domain scaffold

**Files:**
- Create: `pipeline/domains/classes/__init__.py` (empty)
- Create: `tests/domains/classes/__init__.py` (empty)

- [ ] **Step 1: Create empty init files**

```bash
mkdir -p pipeline/domains/classes tests/domains/classes
touch pipeline/domains/classes/__init__.py tests/domains/classes/__init__.py
```

- [ ] **Step 2: Verify pytest discovery**

```bash
py -3 -m pytest tests/domains/classes/ -v
```
Expected: `no tests ran`

---

### Task 6: extract_player_characters.py

**Files:**
- Create: `pipeline/domains/classes/extract_player_characters.py`
- Create: `tests/domains/classes/test_extract_player_characters.py`

Background: `DCGameplayEffectDataAsset` files in `V2/PlayerCharacter/PlayerCharacterEffect/` (44 files). Each file corresponds to one player class (e.g., `Id_PlayerCharacterEffect_Barbarian.json`) and contains base stat values like `StrengthBase`, `VigorBase`, `AgilityBase`, etc. These are entity files keyed by class name.

- [ ] **Step 1: Explore a PlayerCharacterEffect file to confirm stat field names**

```bash
py -3 -c "
import json
from pathlib import Path
f = sorted(Path('raw/DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/PlayerCharacter/PlayerCharacterEffect').glob('*.json'))[0]
d = json.loads(f.read_text(encoding='utf-8'))[0]
props = d.get('Properties', {})
print('File:', f.name, '| Type:', d.get('Type'))
print('Props keys:', list(props.keys()))
for k, v in list(props.items())[:10]:
    print(f'  {k}: {v}')
"
```
Expected: shows stat fields like `StrengthBase`, `VigorBase`, `AgilityBase`, `DexterityBase`, `WillBase`, `KnowledgeBase`, `ResourcefulnessBase`, `MoveSpeedBase`.

- [ ] **Step 2: Write the failing tests**

`tests/domains/classes/test_extract_player_characters.py`:
```python
"""Tests for pipeline/domains/classes/extract_player_characters.py"""
import json
from pathlib import Path
from pipeline.domains.classes.extract_player_characters import (
    extract_player_character, run_player_characters
)


def make_pc_file(tmp_path, pc_id, stats):
    data = [{
        "Type": "DCGameplayEffectDataAsset",
        "Name": pc_id,
        "Properties": stats
    }]
    f = tmp_path / f"{pc_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_player_character_returns_id_and_base_stats(tmp_path):
    f = make_pc_file(tmp_path, "Id_PlayerCharacterEffect_Barbarian", {
        "StrengthBase": 20, "VigorBase": 25, "AgilityBase": 13,
        "DexterityBase": 12, "WillBase": 12, "KnowledgeBase": 8,
        "ResourcefulnessBase": 9, "MoveSpeedBase": 300,
    })
    result = extract_player_character(f)
    assert result is not None
    assert result["id"] == "Id_PlayerCharacterEffect_Barbarian"
    assert result["strength_base"] == 20
    assert result["vigor_base"] == 25
    assert result["move_speed_base"] == 300


def test_extract_player_character_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "Other"}]', encoding="utf-8")
    assert extract_player_character(f) is None


def test_run_player_characters_writes_entity_and_index(tmp_path):
    pc_dir = tmp_path / "pcs"
    pc_dir.mkdir()
    make_pc_file(pc_dir, "Id_PlayerCharacterEffect_Fighter", {
        "StrengthBase": 15, "VigorBase": 20, "AgilityBase": 14,
        "DexterityBase": 14, "WillBase": 15, "KnowledgeBase": 12,
        "ResourcefulnessBase": 10, "MoveSpeedBase": 300,
    })
    extracted = tmp_path / "extracted"
    result = run_player_characters(pc_dir=pc_dir, extracted_root=extracted)
    entity = extracted / "classes" / "Id_PlayerCharacterEffect_Fighter.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["strength_base"] == 15
    assert "_meta" in data
    index = extracted / "classes" / "_index.json"
    assert index.exists()
    assert "Id_PlayerCharacterEffect_Fighter" in result
```

- [ ] **Step 3: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/classes/test_extract_player_characters.py -v
```
Expected: `ImportError`

- [ ] **Step 4: Implement pipeline/domains/classes/extract_player_characters.py**

```python
"""Extract DCGameplayEffectDataAsset (player class base stats) files.

Output: extracted/classes/<id>.json + extracted/classes/_index.json
"""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.writer import Writer

from pipeline.core.normalizer import camel_to_snake

_STAT_FIELDS = (
    "StrengthBase", "VigorBase", "AgilityBase", "DexterityBase",
    "WillBase", "KnowledgeBase", "ResourcefulnessBase", "MoveSpeedBase",
)


def extract_player_character(file_path: Path) -> dict | None:
    """Extract one DCGameplayEffectDataAsset (player class base stats)."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCGameplayEffectDataAsset"), None)
    if not obj:
        return None

    pc_id = obj.get("Name", file_path.stem)
    props = get_properties(obj)

    result: dict = {"id": pc_id}
    for field in _STAT_FIELDS:
        result[camel_to_snake(field)] = props.get(field)

    return result


def run_player_characters(pc_dir: Path, extracted_root: Path) -> dict:
    """Extract all PlayerCharacterEffect files → extracted/classes/<id>.json + _index.json."""
    files = find_files(str(Path(pc_dir) / "Id_PlayerCharacterEffect_*.json"))
    print(f"  [player_characters] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    pcs = {}

    for f in files:
        result = extract_player_character(f)
        if not result:
            continue
        pc_id = result["id"]
        pcs[pc_id] = result
        writer.write_entity("classes", pc_id, result, source_files=[str(f)])
        index_entries.append({
            "id": pc_id,
            "strength_base": result.get("strength_base"),
            "vigor_base": result.get("vigor_base"),
            "move_speed_base": result.get("move_speed_base"),
        })

    writer.write_index("classes", index_entries)
    print(f"  [player_characters] Extracted {len(pcs)} classes")
    return pcs
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/classes/test_extract_player_characters.py -v
```
Expected: all 3 tests PASS

- [ ] **Step 6: Run full suite**

```bash
py -3 -m pytest --tb=short -q
```
Expected: 88 total tests passing

---

### Task 7: extract_perks.py

**Files:**
- Create: `pipeline/domains/classes/extract_perks.py`
- Create: `tests/domains/classes/test_extract_perks.py`

Background: `DCPerkDataAsset` files in `V2/Perk/Perk/` (133 files). Each perk has a name, description, list of classes that can use it, and a list of gameplay ability references.

- [ ] **Step 1: Explore a Perk file to confirm class reference structure**

```bash
py -3 -c "
import json
from pathlib import Path
f = sorted(Path('raw/DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/Perk/Perk').glob('*.json'))[0]
d = json.loads(f.read_text(encoding='utf-8'))[0]
props = d.get('Properties', {})
print('Name:', d.get('Name'))
print('Props keys:', list(props.keys()))
print('Name field:', repr(props.get('Name'))[:80])
print('Classes field:', repr(props.get('Classes'))[:120])
print('DescData:', repr(props.get('DescData'))[:80])
"
```
Expected: shows `Name` (FText), `Classes` (list of `{PrimaryAssetName: "Id_PlayerCharacter_Fighter"}`), `DescData`, `Abilities`.

- [ ] **Step 2: Write the failing tests**

`tests/domains/classes/test_extract_perks.py`:
```python
"""Tests for pipeline/domains/classes/extract_perks.py"""
import json
from pathlib import Path
from pipeline.domains.classes.extract_perks import extract_perk, run_perks


def make_perk_file(tmp_path, perk_id, name_str, class_ids):
    classes = [{"PrimaryAssetType": {"Name": "DesignDataPlayerCharacter"},
                "PrimaryAssetName": c} for c in class_ids]
    data = [{
        "Type": "DCPerkDataAsset",
        "Name": perk_id,
        "Properties": {
            "Name": {"Namespace": "DC", "Key": "k", "LocalizedString": name_str},
            "DescData": {"Namespace": "DC", "Key": "d", "LocalizedString": "A perk"},
            "CanUse": True,
            "Classes": classes,
            "Abilities": [],
        }
    }]
    f = tmp_path / f"{perk_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_perk_returns_id_name_and_classes(tmp_path):
    f = make_perk_file(tmp_path, "Id_Perk_AdrenalineSpike", "Adrenaline Spike",
                       ["Id_PlayerCharacter_Fighter"])
    result = extract_perk(f)
    assert result is not None
    assert result["id"] == "Id_Perk_AdrenalineSpike"
    assert result["name"] == "Adrenaline Spike"
    assert "Id_PlayerCharacter_Fighter" in result["classes"]


def test_extract_perk_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "Other"}]', encoding="utf-8")
    assert extract_perk(f) is None


def test_run_perks_writes_entity_and_index(tmp_path):
    perk_dir = tmp_path / "perks"
    perk_dir.mkdir()
    make_perk_file(perk_dir, "Id_Perk_TestPerk", "Test Perk",
                   ["Id_PlayerCharacter_Fighter", "Id_PlayerCharacter_Barbarian"])
    extracted = tmp_path / "extracted"
    result = run_perks(perk_dir=perk_dir, extracted_root=extracted)
    entity = extracted / "classes" / "Id_Perk_TestPerk.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["name"] == "Test Perk"
    assert len(data["classes"]) == 2
    assert "_meta" in data
    assert "Id_Perk_TestPerk" in result
```

- [ ] **Step 3: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/classes/test_extract_perks.py -v
```
Expected: `ImportError`

- [ ] **Step 4: Implement pipeline/domains/classes/extract_perks.py**

```python
"""Extract DCPerkDataAsset files → extracted/classes/<id>.json + appends to _index.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_text
from pipeline.core.writer import Writer


def _extract_class_ids(classes_list: list) -> list[str]:
    """Extract PrimaryAssetName strings from the Classes array."""
    result = []
    for entry in (classes_list or []):
        if isinstance(entry, dict):
            name = entry.get("PrimaryAssetName")
            if name:
                result.append(name)
    return result


def extract_perk(file_path: Path) -> dict | None:
    """Extract one DCPerkDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCPerkDataAsset"), None)
    if not obj:
        return None

    perk_id = obj.get("Name", file_path.stem)
    props = get_properties(obj)

    return {
        "id": perk_id,
        "name": resolve_text(props.get("Name")),
        "description": resolve_text(props.get("DescData")),
        "can_use": props.get("CanUse", True),
        "classes": _extract_class_ids(props.get("Classes")),
    }


def run_perks(perk_dir: Path, extracted_root: Path) -> dict:
    """Extract all Perk files → extracted/classes/<id>.json entries."""
    files = find_files(str(Path(perk_dir) / "Id_Perk_*.json"))
    print(f"  [perks] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    perks = {}

    for f in files:
        result = extract_perk(f)
        if not result:
            continue
        perk_id = result["id"]
        perks[perk_id] = result
        writer.write_entity("classes", perk_id, result, source_files=[str(f)])
        index_entries.append({
            "id": perk_id,
            "name": result.get("name"),
            "classes": result.get("classes"),
        })

    writer.write_index("classes", index_entries)
    print(f"  [perks] Extracted {len(perks)} perks")
    return perks
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/classes/test_extract_perks.py -v
```
Expected: all 3 tests PASS

- [ ] **Step 6: Run full suite**

```bash
py -3 -m pytest --tb=short -q
```
Expected: 91 total tests passing

---

### Task 8: extract_skills.py

**Files:**
- Create: `pipeline/domains/classes/extract_skills.py`
- Create: `tests/domains/classes/test_extract_skills.py`

Background: `DCSkillDataAsset` files in `V2/Skill/Skill/` (68 files). Similar to perks but with `SkillType`, `SkillTier`, `UseMoving` fields. Skills are abilities active during gameplay.

- [ ] **Step 1: Explore a Skill file to confirm field names**

```bash
py -3 -c "
import json
from pathlib import Path
f = sorted(Path('raw/DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/Skill/Skill').glob('*.json'))[0]
d = json.loads(f.read_text(encoding='utf-8'))[0]
props = d.get('Properties', {})
print('Name:', d.get('Name'), '| Type:', d.get('Type'))
print('Props keys:', list(props.keys())[:12])
for k in ('Name', 'DescData', 'SkillType', 'SkillTier', 'UseMoving', 'Classes', 'SkillTag'):
    print(f'  {k}:', repr(props.get(k))[:80])
"
```

- [ ] **Step 2: Write the failing tests**

`tests/domains/classes/test_extract_skills.py`:
```python
"""Tests for pipeline/domains/classes/extract_skills.py"""
import json
from pathlib import Path
from pipeline.domains.classes.extract_skills import extract_skill, run_skills


def make_skill_file(tmp_path, skill_id, name_str, skill_type_tag, tier=1):
    data = [{
        "Type": "DCSkillDataAsset",
        "Name": skill_id,
        "Properties": {
            "Name": {"Namespace": "DC", "Key": "k", "LocalizedString": name_str},
            "DescData": {"Namespace": "DC", "Key": "d", "LocalizedString": "Desc"},
            "SkillType": {"TagName": skill_type_tag},
            "SkillTier": tier,
            "UseMoving": True,
            "Classes": [{"PrimaryAssetType": {"Name": "DesignDataPlayerCharacter"},
                         "PrimaryAssetName": "Id_PlayerCharacter_Barbarian"}],
        }
    }]
    f = tmp_path / f"{skill_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_skill_returns_id_name_and_type(tmp_path):
    f = make_skill_file(tmp_path, "Id_Skill_AchillesStrike", "Achilles Strike",
                        "Type.Skill.Instant", tier=1)
    result = extract_skill(f)
    assert result is not None
    assert result["id"] == "Id_Skill_AchillesStrike"
    assert result["name"] == "Achilles Strike"
    assert result["skill_type"] == "Type.Skill.Instant"
    assert result["skill_tier"] == 1


def test_extract_skill_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "Other"}]', encoding="utf-8")
    assert extract_skill(f) is None


def test_run_skills_writes_entity_and_index(tmp_path):
    skill_dir = tmp_path / "skills"
    skill_dir.mkdir()
    make_skill_file(skill_dir, "Id_Skill_TestSkill", "Test Skill", "Type.Skill.Toggle")
    extracted = tmp_path / "extracted"
    result = run_skills(skill_dir=skill_dir, extracted_root=extracted)
    entity = extracted / "classes" / "Id_Skill_TestSkill.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["name"] == "Test Skill"
    assert "_meta" in data
    assert "Id_Skill_TestSkill" in result
```

- [ ] **Step 3: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/classes/test_extract_skills.py -v
```
Expected: `ImportError`

- [ ] **Step 4: Implement pipeline/domains/classes/extract_skills.py**

```python
"""Extract DCSkillDataAsset files → extracted/classes/<id>.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_text, resolve_tag
from pipeline.core.writer import Writer


def _extract_class_ids(classes_list: list) -> list[str]:
    """Extract PrimaryAssetName strings from the Classes array."""
    result = []
    for entry in (classes_list or []):
        if isinstance(entry, dict):
            name = entry.get("PrimaryAssetName")
            if name:
                result.append(name)
    return result


def extract_skill(file_path: Path) -> dict | None:
    """Extract one DCSkillDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCSkillDataAsset"), None)
    if not obj:
        return None

    skill_id = obj.get("Name", file_path.stem)
    props = get_properties(obj)

    return {
        "id": skill_id,
        "name": resolve_text(props.get("Name")),
        "description": resolve_text(props.get("DescData")),
        "skill_type": resolve_tag(props.get("SkillType")),
        "skill_tier": props.get("SkillTier"),
        "use_moving": props.get("UseMoving", False),
        "classes": _extract_class_ids(props.get("Classes")),
    }


def run_skills(skill_dir: Path, extracted_root: Path) -> dict:
    """Extract all Skill files → extracted/classes/<id>.json."""
    files = find_files(str(Path(skill_dir) / "Id_Skill_*.json"))
    print(f"  [skills] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    skills = {}

    for f in files:
        result = extract_skill(f)
        if not result:
            continue
        skill_id = result["id"]
        skills[skill_id] = result
        writer.write_entity("classes", skill_id, result, source_files=[str(f)])
        index_entries.append({
            "id": skill_id,
            "name": result.get("name"),
            "skill_type": result.get("skill_type"),
            "skill_tier": result.get("skill_tier"),
            "classes": result.get("classes"),
        })

    writer.write_index("classes", index_entries)
    print(f"  [skills] Extracted {len(skills)} skills")
    return skills
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/classes/test_extract_skills.py -v
```
Expected: all 3 tests PASS

- [ ] **Step 6: Run full suite**

```bash
py -3 -m pytest --tb=short -q
```
Expected: 94 total tests passing

---

## Chunk 3: Classes Domain (cont.) + Monsters Domain + Final

### Task 9: extract_shapeshifts.py

**Files:**
- Create: `pipeline/domains/classes/extract_shapeshifts.py`
- Create: `tests/domains/classes/test_extract_shapeshifts.py`

Background: `DCShapeShiftDataAsset` files in `V2/ShapeShift/ShapeShift/` (7 files). Each shapeshift form has a name, description, casting time, capsule scaling, and associated gameplay tags.

- [ ] **Step 1: Explore a ShapeShift file to confirm field names**

```bash
py -3 -c "
import json
from pathlib import Path
f = sorted(Path('raw/DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/ShapeShift/ShapeShift').glob('*.json'))[0]
d = json.loads(f.read_text(encoding='utf-8'))[0]
props = d.get('Properties', {})
print('Name:', d.get('Name'), '| Type:', d.get('Type'))
print('Props keys:', list(props.keys()))
for k in ('Name', 'Desc', 'Classes', 'CastingTime', 'ShapeShiftTag', 'CapsuleRadiusScale', 'CapsuleHeightScale'):
    print(f'  {k}:', repr(props.get(k))[:80])
"
```

- [ ] **Step 2: Write the failing tests**

`tests/domains/classes/test_extract_shapeshifts.py`:
```python
"""Tests for pipeline/domains/classes/extract_shapeshifts.py"""
import json
from pathlib import Path
from pipeline.domains.classes.extract_shapeshifts import extract_shapeshift, run_shapeshifts


def make_shapeshift_file(tmp_path, ss_id, name_str, casting_time=1.0):
    data = [{
        "Type": "DCShapeShiftDataAsset",
        "Name": ss_id,
        "Properties": {
            "Name": {"Namespace": "DC", "Key": "k", "LocalizedString": name_str},
            "Desc": {"Namespace": "DC", "Key": "d", "LocalizedString": "Desc"},
            "CastingTime": casting_time,
            "CapsuleRadiusScale": 2.05,
            "CapsuleHeightScale": 1.0,
            "ShapeShiftTag": {"TagName": "Ability.ShapeShift.Bear"},
            "Classes": [{"PrimaryAssetType": {"Name": "DesignDataPlayerCharacter"},
                         "PrimaryAssetName": "Id_PlayerCharacter_Druid"}],
        }
    }]
    f = tmp_path / f"{ss_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_shapeshift_returns_id_and_fields(tmp_path):
    f = make_shapeshift_file(tmp_path, "Id_ShapeShift_Bear", "Bear", casting_time=1.0)
    result = extract_shapeshift(f)
    assert result is not None
    assert result["id"] == "Id_ShapeShift_Bear"
    assert result["name"] == "Bear"
    assert result["casting_time"] == 1.0
    assert result["shapeshift_tag"] == "Ability.ShapeShift.Bear"
    assert "Id_PlayerCharacter_Druid" in result["classes"]


def test_extract_shapeshift_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "Other"}]', encoding="utf-8")
    assert extract_shapeshift(f) is None


def test_run_shapeshifts_writes_entity_and_index(tmp_path):
    ss_dir = tmp_path / "ss"
    ss_dir.mkdir()
    make_shapeshift_file(ss_dir, "Id_ShapeShift_Panther", "Panther", casting_time=0.5)
    extracted = tmp_path / "extracted"
    result = run_shapeshifts(ss_dir=ss_dir, extracted_root=extracted)
    entity = extracted / "classes" / "Id_ShapeShift_Panther.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["name"] == "Panther"
    assert "_meta" in data
    index = extracted / "classes" / "_index.json"
    assert index.exists()
    assert "Id_ShapeShift_Panther" in result
```

- [ ] **Step 3: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/classes/test_extract_shapeshifts.py -v
```
Expected: `ImportError`

- [ ] **Step 4: Implement pipeline/domains/classes/extract_shapeshifts.py**

```python
"""Extract DCShapeShiftDataAsset files → extracted/classes/<id>.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_text, resolve_tag
from pipeline.core.writer import Writer


def extract_shapeshift(file_path: Path) -> dict | None:
    """Extract one DCShapeShiftDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCShapeShiftDataAsset"), None)
    if not obj:
        return None

    ss_id = obj.get("Name", file_path.stem)
    props = get_properties(obj)

    classes = []
    for entry in (props.get("Classes") or []):
        if isinstance(entry, dict):
            name = entry.get("PrimaryAssetName")
            if name:
                classes.append(name)

    return {
        "id": ss_id,
        "name": resolve_text(props.get("Name")),
        "description": resolve_text(props.get("Desc")),
        "casting_time": props.get("CastingTime"),
        "capsule_radius_scale": props.get("CapsuleRadiusScale"),
        "capsule_height_scale": props.get("CapsuleHeightScale"),
        "shapeshift_tag": resolve_tag(props.get("ShapeShiftTag")),
        "classes": classes,
    }


def run_shapeshifts(ss_dir: Path, extracted_root: Path) -> dict:
    """Extract all ShapeShift files → extracted/classes/<id>.json."""
    files = find_files(str(Path(ss_dir) / "Id_ShapeShift_*.json"))
    print(f"  [shapeshifts] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    shapeshifts = {}

    for f in files:
        result = extract_shapeshift(f)
        if not result:
            continue
        ss_id = result["id"]
        shapeshifts[ss_id] = result
        writer.write_entity("classes", ss_id, result, source_files=[str(f)])
        index_entries.append({
            "id": ss_id,
            "name": result.get("name"),
            "shapeshift_tag": result.get("shapeshift_tag"),
            "classes": result.get("classes"),
        })

    writer.write_index("classes", index_entries)
    print(f"  [shapeshifts] Extracted {len(shapeshifts)} shapeshifts")
    return shapeshifts
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/classes/test_extract_shapeshifts.py -v
```
Expected: all 3 tests PASS

- [ ] **Step 6: Run full suite**

```bash
py -3 -m pytest --tb=short -q
```
Expected: 97 total tests passing

---

### Task 10: classes domain __init__.py + smoke test

**Files:**
- Modify: `pipeline/domains/classes/__init__.py`
- Create: `tests/domains/classes/test_classes_run.py`

- [ ] **Step 1: Implement run()**

`pipeline/domains/classes/__init__.py`:
```python
"""Classes domain extractor — run() called by extract_all.py orchestrator."""
from pathlib import Path

from pipeline.domains.classes.extract_player_characters import run_player_characters
from pipeline.domains.classes.extract_perks import run_perks
from pipeline.domains.classes.extract_skills import run_skills
from pipeline.domains.classes.extract_shapeshifts import run_shapeshifts
from pipeline.core.writer import Writer

_V2_BASE = "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2"


def run(raw_root: Path, extracted_root: Path) -> dict:
    """Run all classes domain extractors. Returns summary of counts.

    NOTE: Individual run_* functions each write a partial _index.json as a
    side-effect (useful for standalone runs / unit tests). This orchestrator
    overwrites that partial index with a single combined index containing all
    entity types at the end.
    """
    print("[classes] Starting extraction...")
    summary = {}
    all_entities: dict[str, dict] = {}

    dirs = {
        "pc": raw_root / _V2_BASE / "PlayerCharacter" / "PlayerCharacterEffect",
        "perk": raw_root / _V2_BASE / "Perk" / "Perk",
        "skill": raw_root / _V2_BASE / "Skill" / "Skill",
        "shapeshift": raw_root / _V2_BASE / "ShapeShift" / "ShapeShift",
    }

    if dirs["pc"].exists():
        pcs = run_player_characters(pc_dir=dirs["pc"], extracted_root=extracted_root)
        summary["player_characters"] = len(pcs)
        all_entities.update({k: {**v, "_entity_type": "player_character"}
                             for k, v in pcs.items()})
    else:
        print(f"  [classes] WARNING: {dirs['pc']} not found")
        summary["player_characters"] = 0

    if dirs["perk"].exists():
        perks = run_perks(perk_dir=dirs["perk"], extracted_root=extracted_root)
        summary["perks"] = len(perks)
        all_entities.update({k: {**v, "_entity_type": "perk"}
                             for k, v in perks.items()})
    else:
        print(f"  [classes] WARNING: {dirs['perk']} not found")
        summary["perks"] = 0

    if dirs["skill"].exists():
        skills = run_skills(skill_dir=dirs["skill"], extracted_root=extracted_root)
        summary["skills"] = len(skills)
        all_entities.update({k: {**v, "_entity_type": "skill"}
                             for k, v in skills.items()})
    else:
        print(f"  [classes] WARNING: {dirs['skill']} not found")
        summary["skills"] = 0

    if dirs["shapeshift"].exists():
        ss = run_shapeshifts(ss_dir=dirs["shapeshift"], extracted_root=extracted_root)
        summary["shapeshifts"] = len(ss)
        all_entities.update({k: {**v, "_entity_type": "shapeshift"}
                             for k, v in ss.items()})
    else:
        print(f"  [classes] WARNING: {dirs['shapeshift']} not found")
        summary["shapeshifts"] = 0

    # Write combined index with ALL entity types (overwrites partial indexes
    # written by individual run_* functions above)
    combined_index = [
        {"id": v["id"], "name": v.get("name"), "type": v["_entity_type"]}
        for v in all_entities.values()
    ]
    Writer(extracted_root).write_index("classes", combined_index)

    print(f"[classes] Done. Summary: {summary}")
    return summary
```

- [ ] **Step 2: Write smoke test**

`tests/domains/classes/test_classes_run.py`:
```python
"""Smoke test for classes domain run() function."""
from pathlib import Path
from pipeline.domains.classes import run


def test_classes_run_smoke(tmp_path):
    """run() completes without error on empty raw dirs."""
    import json
    raw = tmp_path / "raw"
    raw.mkdir()
    extracted = tmp_path / "extracted"
    summary = run(raw_root=raw, extracted_root=extracted)
    assert isinstance(summary, dict)
    required_keys = ("player_characters", "perks", "skills", "shapeshifts")
    assert all(k in summary for k in required_keys)
    assert all(isinstance(summary[k], int) for k in required_keys)
    # Combined index is always written (may be empty if all dirs missing)
    index_path = extracted / "classes" / "_index.json"
    assert index_path.exists()
    data = json.loads(index_path.read_text(encoding="utf-8"))
    assert "count" in data
```

- [ ] **Step 3: Run smoke test + full suite**

```bash
py -3 -m pytest tests/domains/classes/test_classes_run.py -v
py -3 -m pytest --tb=short -q
```
Expected: smoke test passes, 98 total tests passing

---

### Task 11: Monsters domain scaffold

**Files:**
- Create: `pipeline/domains/monsters/__init__.py` (empty)
- Create: `tests/domains/monsters/__init__.py` (empty)

- [ ] **Step 1: Create empty init files**

```bash
mkdir -p pipeline/domains/monsters tests/domains/monsters
touch pipeline/domains/monsters/__init__.py tests/domains/monsters/__init__.py
```

- [ ] **Step 2: Verify pytest discovery**

```bash
py -3 -m pytest tests/domains/monsters/ -v
```
Expected: `no tests ran`

---

### Task 12: extract_monsters.py

**Files:**
- Create: `pipeline/domains/monsters/extract_monsters.py`
- Create: `tests/domains/monsters/test_extract_monsters.py`

Background: `DCMonsterDataAsset` files in `V2/Monster/Monster/` (392 files). Key wiki-relevant fields: `IdTag`, `ClassType`, `GradeType`, `CharacterTypes`, `Name`, `AdvPoint`, `ExpPoint`.

- [ ] **Step 1: Explore a Monster file to confirm field names and Name field location**

```bash
py -3 -c "
import json
from pathlib import Path
f = sorted(Path('raw/DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/Monster/Monster').glob('*.json'))[0]
d = json.loads(f.read_text(encoding='utf-8'))[0]
props = d.get('Properties', {})
print('Name:', d.get('Name'), '| Type:', d.get('Type'))
print('Props keys:', list(props.keys())[:15])
for k in ('IdTag', 'Name', 'ClassType', 'GradeType', 'CharacterTypes', 'AdvPoint', 'ExpPoint'):
    print(f'  {k}:', repr(props.get(k))[:80])
"
```
Expected: confirms `IdTag` (tag), `ClassType` (tag), `GradeType` (tag), `AdvPoint`/`ExpPoint` (int), `Name` may be an FText or absent (monster name may be derived from IdTag).

- [ ] **Step 2: Write the failing tests**

`tests/domains/monsters/test_extract_monsters.py`:
```python
"""Tests for pipeline/domains/monsters/extract_monsters.py"""
import json
from pathlib import Path
from pipeline.domains.monsters.extract_monsters import extract_monster, run_monsters


def make_monster_file(tmp_path, monster_id, id_tag, class_type, grade_type, adv=50, exp=8):
    data = [{
        "Type": "DCMonsterDataAsset",
        "Name": monster_id,
        "Properties": {
            "IdTag": {"TagName": id_tag},
            "ClassType": {"TagName": class_type},
            "GradeType": {"TagName": grade_type},
            "CharacterTypes": [{"TagName": "Type.Character.Undead.Skeleton"}],
            "AdvPoint": adv,
            "ExpPoint": exp,
        }
    }]
    f = tmp_path / f"{monster_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_monster_returns_id_and_fields(tmp_path):
    f = make_monster_file(
        tmp_path, "Id_Monster_Skeleton_Common",
        "Id.Monster.Skeleton", "Type.Monster.Class.Normal",
        "Type.Monster.Grade.Common", adv=5, exp=2
    )
    result = extract_monster(f)
    assert result is not None
    assert result["id"] == "Id_Monster_Skeleton_Common"
    assert result["id_tag"] == "Id.Monster.Skeleton"
    assert result["class_type"] == "Type.Monster.Class.Normal"
    assert result["grade_type"] == "Type.Monster.Grade.Common"
    assert result["adv_point"] == 5
    assert result["exp_point"] == 2
    assert "Type.Character.Undead.Skeleton" in result["character_types"]


def test_extract_monster_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "Other"}]', encoding="utf-8")
    assert extract_monster(f) is None


def test_run_monsters_writes_entity_and_index(tmp_path):
    mon_dir = tmp_path / "monsters"
    mon_dir.mkdir()
    make_monster_file(mon_dir, "Id_Monster_Skeleton_Common",
                      "Id.Monster.Skeleton", "Type.Monster.Class.Normal",
                      "Type.Monster.Grade.Common")
    extracted = tmp_path / "extracted"
    result = run_monsters(monster_dir=mon_dir, extracted_root=extracted)
    entity = extracted / "monsters" / "Id_Monster_Skeleton_Common.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id_tag"] == "Id.Monster.Skeleton"
    assert "_meta" in data
    index = extracted / "monsters" / "_index.json"
    assert index.exists()
    assert "Id_Monster_Skeleton_Common" in result
```

- [ ] **Step 3: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/monsters/test_extract_monsters.py -v
```
Expected: `ImportError`

- [ ] **Step 4: Implement pipeline/domains/monsters/extract_monsters.py**

```python
"""Extract DCMonsterDataAsset files → extracted/monsters/<id>.json + _index.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_tag, resolve_text
from pipeline.core.writer import Writer


def extract_monster(file_path: Path) -> dict | None:
    """Extract one DCMonsterDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCMonsterDataAsset"), None)
    if not obj:
        return None

    monster_id = obj.get("Name", file_path.stem)
    props = get_properties(obj)

    character_types = [
        resolve_tag(t) for t in (props.get("CharacterTypes") or [])
        if resolve_tag(t) is not None
    ]

    return {
        "id": monster_id,
        "id_tag": resolve_tag(props.get("IdTag")),
        "name": resolve_text(props.get("Name")),
        "class_type": resolve_tag(props.get("ClassType")),
        "grade_type": resolve_tag(props.get("GradeType")),
        "character_types": character_types,
        "adv_point": props.get("AdvPoint"),
        "exp_point": props.get("ExpPoint"),
    }


def run_monsters(monster_dir: Path, extracted_root: Path) -> dict:
    """Extract all Monster files → extracted/monsters/<id>.json + _index.json."""
    files = find_files(str(Path(monster_dir) / "Id_Monster_*.json"))
    print(f"  [monsters] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    monsters = {}

    for f in files:
        result = extract_monster(f)
        if not result:
            continue
        monster_id = result["id"]
        monsters[monster_id] = result
        writer.write_entity("monsters", monster_id, result, source_files=[str(f)])
        index_entries.append({
            "id": monster_id,
            "id_tag": result.get("id_tag"),
            "class_type": result.get("class_type"),
            "grade_type": result.get("grade_type"),
            "adv_point": result.get("adv_point"),
            "exp_point": result.get("exp_point"),
        })

    writer.write_index("monsters", index_entries)
    print(f"  [monsters] Extracted {len(monsters)} monsters")
    return monsters
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/monsters/test_extract_monsters.py -v
```
Expected: all 3 tests PASS

- [ ] **Step 6: Run full suite**

```bash
py -3 -m pytest --tb=short -q
```
Expected: 101 total tests passing

---

### Task 13: monsters domain __init__.py + smoke test

**Files:**
- Modify: `pipeline/domains/monsters/__init__.py`
- Create: `tests/domains/monsters/test_monsters_run.py`

- [ ] **Step 1: Implement run()**

`pipeline/domains/monsters/__init__.py`:
```python
"""Monsters domain extractor — run() called by extract_all.py orchestrator."""
from pathlib import Path

from pipeline.domains.monsters.extract_monsters import run_monsters

_V2_BASE = "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2"


def run(raw_root: Path, extracted_root: Path) -> dict:
    """Run the monsters domain extractor. Returns summary of counts."""
    print("[monsters] Starting extraction...")
    summary = {}

    monster_dir = raw_root / _V2_BASE / "Monster" / "Monster"
    if monster_dir.exists():
        monsters = run_monsters(monster_dir=monster_dir, extracted_root=extracted_root)
        summary["monsters"] = len(monsters)
    else:
        print(f"  [monsters] WARNING: {monster_dir} not found")
        summary["monsters"] = 0

    print(f"[monsters] Done. Summary: {summary}")
    return summary
```

- [ ] **Step 2: Write smoke test**

`tests/domains/monsters/test_monsters_run.py`:
```python
"""Smoke test for monsters domain run() function."""
from pathlib import Path
from pipeline.domains.monsters import run


def test_monsters_run_smoke(tmp_path):
    """run() completes without error on empty raw dirs."""
    raw = tmp_path / "raw"
    raw.mkdir()
    extracted = tmp_path / "extracted"
    summary = run(raw_root=raw, extracted_root=extracted)
    assert isinstance(summary, dict)
    assert "monsters" in summary
    assert isinstance(summary["monsters"], int)
```

- [ ] **Step 3: Run smoke test + full suite**

```bash
py -3 -m pytest tests/domains/monsters/test_monsters_run.py -v
py -3 -m pytest --tb=short -q
```
Expected: smoke test passes, 102 total tests passing

---

## Final: Integration Test + Verification

### Task 14: Integration test on real raw/ data

- [ ] **Step 1: Run all three domain extractors against real data**

```bash
py -3 -c "
from pathlib import Path
from pipeline.domains.items import run as items_run
from pipeline.domains.classes import run as classes_run
from pipeline.domains.monsters import run as monsters_run

raw = Path('raw')
extracted = Path('extracted')

print('=== items ===')
s1 = items_run(raw_root=raw, extracted_root=extracted)
print('Summary:', s1)
assert s1['items'] > 0, 'Expected items > 0'
assert s1['items_with_properties'] > 0, 'Expected some items to have properties merged'

print('=== classes ===')
s2 = classes_run(raw_root=raw, extracted_root=extracted)
print('Summary:', s2)
assert s2['perks'] > 0, 'Expected perks > 0'
assert s2['skills'] > 0, 'Expected skills > 0'

print('=== monsters ===')
s3 = monsters_run(raw_root=raw, extracted_root=extracted)
print('Summary:', s3)
assert s3['monsters'] > 0, 'Expected monsters > 0'

print('All assertions passed.')
"
```

- [ ] **Step 2: Spot-check a few output files**

```bash
py -3 -c "
import json
from pathlib import Path

# Check one item entity file
items = list(Path('extracted/items').glob('Id_Item_*.json'))
print(f'Item entity files: {len(items)}')
if items:
    d = json.loads(items[0].read_text(encoding='utf-8'))
    print('  id:', d.get('id'))
    print('  name:', d.get('name'))
    print('  item_type:', d.get('item_type'))
    print('  properties count:', len(d.get('properties', [])))
    print('  _meta present:', '_meta' in d)

# Check index
idx = json.loads(Path('extracted/items/_index.json').read_text(encoding='utf-8'))
print(f'Items index count: {idx[\"count\"]}')

# Check one monster
monsters = list(Path('extracted/monsters').glob('Id_Monster_*.json'))
print(f'Monster entity files: {len(monsters)}')
if monsters:
    d = json.loads(monsters[0].read_text(encoding='utf-8'))
    print('  id_tag:', d.get('id_tag'))
    print('  class_type:', d.get('class_type'))

# Verify classes combined index contains multiple entity types
classes_idx = json.loads(Path('extracted/classes/_index.json').read_text(encoding='utf-8'))
print(f'Classes index count: {classes_idx[\"count\"]}')
types_in_index = {e.get('type') for e in classes_idx.get('entries', [])}
print(f'  Entity types in index: {types_in_index}')
assert len(types_in_index) > 1, f'Classes index should have multiple entity types, got: {types_in_index}'
print('Classes index OK.')
"
```

- [ ] **Step 3: Run full test suite**

```bash
py -3 -m pytest tests/ --tb=short -q
```
Expected: all 102 tests passing

- [ ] **Step 4: Verify directory structure**

```bash
find pipeline/domains -type f -name "*.py" | sort
```
Expected to include:
```
pipeline/domains/classes/__init__.py
pipeline/domains/classes/extract_perks.py
pipeline/domains/classes/extract_player_characters.py
pipeline/domains/classes/extract_shapeshifts.py
pipeline/domains/classes/extract_skills.py
pipeline/domains/engine/__init__.py
pipeline/domains/engine/extract_constants.py
pipeline/domains/engine/extract_curves.py
pipeline/domains/engine/extract_enums.py
pipeline/domains/engine/extract_tags.py
pipeline/domains/items/__init__.py
pipeline/domains/items/extract_item_properties.py
pipeline/domains/items/extract_items.py
pipeline/domains/monsters/__init__.py
pipeline/domains/monsters/extract_monsters.py
```
