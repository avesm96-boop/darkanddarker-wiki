# Phase 4b: Spawns Domain Extractor Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `pipeline/domains/spawns/` with 4 sub-extractors producing `extracted/spawns/<id>.json` entity files and a combined `_index.json`.

**Architecture:** Each sub-extractor is a focused module with one `extract_*()` function and one `run_*()` function. `__init__.py` orchestrates all four sub-extractors and writes a single combined index, following the exact pattern of `pipeline/domains/combat/__init__.py`. `extract_spawners.py`, `extract_loot_drops.py`, and `extract_loot_drop_groups.py` each define a local `_extract_asset_id()` helper (same pattern as `extract_aoes.py`).

**Tech Stack:** Python 3.10+, pytest, pathlib, pipeline.core (reader, writer, normalizer)

**Spec:** `docs/superpowers/specs/2026-03-12-phase4-dungeons-spawns-design.md` §2.2, §3, §4.2, §5.2, §6, §7, §8

---

## Chunk 1: Test Infrastructure + Spawners + LootDrops

### File Map

- Create: `pipeline/domains/spawns/__init__.py` (stub then full orchestrator)
- Create: `pipeline/domains/spawns/extract_spawners.py`
- Create: `pipeline/domains/spawns/extract_loot_drops.py`
- Create: `tests/domains/spawns/__init__.py`
- Create: `tests/domains/spawns/test_extract_spawners.py`
- Create: `tests/domains/spawns/test_extract_loot_drops.py`

---

### Task 1: Test infrastructure

**Files:**
- Create: `pipeline/domains/spawns/__init__.py` (empty stub)
- Create: `tests/domains/spawns/__init__.py` (empty)

- [ ] **Step 1: Create the two empty `__init__.py` files**

`pipeline/domains/spawns/__init__.py`:
```python
"""Spawns domain extractor — run() called by extract_all.py orchestrator."""
```

`tests/domains/spawns/__init__.py`:
```python
```
(empty file)

- [ ] **Step 2: Verify pytest can collect from the new directory**

Run from `darkanddarker-wiki/`:
```bash
py -3 -m pytest tests/domains/spawns/ --collect-only
```
Expected: `no tests ran`

---

### Task 2: extract_spawners.py — DCSpawnerDataAsset

**Files:**
- Create: `pipeline/domains/spawns/extract_spawners.py`
- Create: `tests/domains/spawns/test_extract_spawners.py`

- [ ] **Step 1: Write the failing tests**

`tests/domains/spawns/test_extract_spawners.py`:
```python
"""Tests for pipeline/domains/spawns/extract_spawners.py"""
import json
from pathlib import Path
from pipeline.domains.spawns.extract_spawners import extract_spawner, run_spawners


def make_spawner_file(tmp_path, spawner_id):
    data = [{
        "Type": "DCSpawnerDataAsset",
        "Name": spawner_id,
        "Properties": {
            "SpawnerItemArray": [
                {
                    "SpawnRate": 0.5,
                    "DungeonGrades": [1, 2, 3],
                    "LootDropGroupId": {
                        "AssetPathName": "/Game/.../LDG_Chest.LDG_Chest", "SubPathString": ""},
                    "MonsterId": {
                        "AssetPathName": "/Game/.../M_Skeleton.M_Skeleton", "SubPathString": ""},
                    "PropsId": None,
                }
            ]
        }
    }]
    f = tmp_path / f"{spawner_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_spawner_returns_id_and_fields(tmp_path):
    f = make_spawner_file(tmp_path, "Id_Spawner_SkeletonChest")
    result = extract_spawner(f)
    assert result is not None
    assert result["id"] == "Id_Spawner_SkeletonChest"
    assert isinstance(result["spawner_items"], list)
    assert len(result["spawner_items"]) == 1
    item = result["spawner_items"][0]
    assert item["spawn_rate"] == 0.5
    assert item["dungeon_grades"] == [1, 2, 3]
    assert item["loot_drop_group_id"] == "LDG_Chest"
    assert item["monster_id"] == "M_Skeleton"
    assert item["props_id"] is None


def test_extract_spawner_handles_empty_items(tmp_path):
    data = [{"Type": "DCSpawnerDataAsset", "Name": "Id_Spawner_Empty",
             "Properties": {"SpawnerItemArray": []}}]
    f = tmp_path / "empty.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    result = extract_spawner(f)
    assert result is not None
    assert result["spawner_items"] == []


def test_extract_spawner_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_spawner(f) is None


def test_run_spawners_writes_entity_and_index(tmp_path):
    spawner_dir = tmp_path / "spawners"
    spawner_dir.mkdir()
    make_spawner_file(spawner_dir, "Id_Spawner_SkeletonChest")
    extracted = tmp_path / "extracted"
    result = run_spawners(spawner_dir=spawner_dir, extracted_root=extracted)
    entity = extracted / "spawns" / "Id_Spawner_SkeletonChest.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id"] == "Id_Spawner_SkeletonChest"
    assert isinstance(data["spawner_items"], list)
    assert "_meta" in data
    index = extracted / "spawns" / "_index.json"
    assert index.exists()
    assert "Id_Spawner_SkeletonChest" in result
```

- [ ] **Step 2: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/spawns/test_extract_spawners.py -v
```
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement pipeline/domains/spawns/extract_spawners.py**

```python
"""Extract DCSpawnerDataAsset files → extracted/spawns/<id>.json + _index.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.writer import Writer


def _extract_asset_id(ref: dict) -> str | None:
    """Extract asset ID from {"AssetPathName": "/Game/.../Foo.Foo", "SubPathString": ""}."""
    if not isinstance(ref, dict):
        return None
    asset_path = ref.get("AssetPathName", "")
    if not asset_path:
        return None
    parts = asset_path.split(".")
    return parts[-1] if len(parts) > 1 else None


def extract_spawner(file_path: Path) -> dict | None:
    """Extract one DCSpawnerDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError):
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCSpawnerDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    spawner_items = [
        {
            "spawn_rate": item.get("SpawnRate"),
            "dungeon_grades": item.get("DungeonGrades") or [],
            "loot_drop_group_id": _extract_asset_id(item.get("LootDropGroupId")),
            "monster_id": _extract_asset_id(item.get("MonsterId")),
            "props_id": _extract_asset_id(item.get("PropsId")),
        }
        for item in (props.get("SpawnerItemArray") or [])
    ]

    return {
        "id": obj["Name"],
        "spawner_items": spawner_items,
    }


def run_spawners(spawner_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCSpawnerDataAsset files."""
    files = find_files(str(Path(spawner_dir) / "*.json"))
    print(f"  [spawners] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    spawners = {}

    for f in files:
        result = extract_spawner(f)
        if not result:
            continue
        spawner_id = result["id"]
        spawners[spawner_id] = result
        writer.write_entity("spawns", spawner_id, result, source_files=[str(f)])
        index_entries.append({"id": spawner_id})

    writer.write_index("spawns", index_entries)
    print(f"  [spawners] Extracted {len(spawners)} spawners")
    return spawners
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/spawns/test_extract_spawners.py -v
```
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/spawns/__init__.py pipeline/domains/spawns/extract_spawners.py tests/domains/spawns/__init__.py tests/domains/spawns/test_extract_spawners.py
git commit -m "feat: add spawns domain + extract_spawners extractor"
```

---

### Task 3: extract_loot_drops.py — DCLootDropDataAsset

**Files:**
- Create: `pipeline/domains/spawns/extract_loot_drops.py`
- Create: `tests/domains/spawns/test_extract_loot_drops.py`

- [ ] **Step 1: Write the failing tests**

`tests/domains/spawns/test_extract_loot_drops.py`:
```python
"""Tests for pipeline/domains/spawns/extract_loot_drops.py"""
import json
from pathlib import Path
from pipeline.domains.spawns.extract_loot_drops import extract_loot_drop, run_loot_drops


def make_loot_drop_file(tmp_path, drop_id):
    data = [{
        "Type": "DCLootDropDataAsset",
        "Name": drop_id,
        "Properties": {
            "LootDropItemArray": [
                {
                    "ItemId": {"AssetPathName": "/Game/.../Id_Item_Sword.Id_Item_Sword",
                               "SubPathString": ""},
                    "ItemCount": 1,
                    "LuckGrade": 3,
                },
                {
                    "ItemId": {"AssetPathName": "/Game/.../Id_Item_Shield.Id_Item_Shield",
                               "SubPathString": ""},
                    "ItemCount": 2,
                    "LuckGrade": 1,
                },
            ]
        }
    }]
    f = tmp_path / f"{drop_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_loot_drop_returns_id_and_items(tmp_path):
    f = make_loot_drop_file(tmp_path, "ID_Lootdrop_SwordBundle")
    result = extract_loot_drop(f)
    assert result is not None
    assert result["id"] == "ID_Lootdrop_SwordBundle"
    assert isinstance(result["items"], list)
    assert len(result["items"]) == 2
    item = result["items"][0]
    assert item["item_id"] == "Id_Item_Sword"
    assert item["item_count"] == 1
    assert item["luck_grade"] == 3


def test_extract_loot_drop_handles_empty_items(tmp_path):
    data = [{"Type": "DCLootDropDataAsset", "Name": "ID_Lootdrop_Empty",
             "Properties": {"LootDropItemArray": []}}]
    f = tmp_path / "empty.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    result = extract_loot_drop(f)
    assert result is not None
    assert result["items"] == []


def test_extract_loot_drop_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_loot_drop(f) is None


def test_run_loot_drops_writes_entity_and_index(tmp_path):
    drops_dir = tmp_path / "drops"
    drops_dir.mkdir()
    make_loot_drop_file(drops_dir, "ID_Lootdrop_SwordBundle")
    extracted = tmp_path / "extracted"
    result = run_loot_drops(loot_drop_dir=drops_dir, extracted_root=extracted)
    entity = extracted / "spawns" / "ID_Lootdrop_SwordBundle.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id"] == "ID_Lootdrop_SwordBundle"
    assert len(data["items"]) == 2
    assert "_meta" in data
    index = extracted / "spawns" / "_index.json"
    assert index.exists()
    assert "ID_Lootdrop_SwordBundle" in result
```

- [ ] **Step 2: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/spawns/test_extract_loot_drops.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement pipeline/domains/spawns/extract_loot_drops.py**

```python
"""Extract DCLootDropDataAsset files → extracted/spawns/<id>.json + _index.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.writer import Writer


def _extract_asset_id(ref: dict) -> str | None:
    """Extract asset ID from {"AssetPathName": "/Game/.../Foo.Foo", "SubPathString": ""}."""
    if not isinstance(ref, dict):
        return None
    asset_path = ref.get("AssetPathName", "")
    if not asset_path:
        return None
    parts = asset_path.split(".")
    return parts[-1] if len(parts) > 1 else None


def extract_loot_drop(file_path: Path) -> dict | None:
    """Extract one DCLootDropDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError):
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCLootDropDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    items = [
        {
            "item_id": _extract_asset_id(item.get("ItemId")),
            "item_count": item.get("ItemCount"),
            "luck_grade": item.get("LuckGrade"),
        }
        for item in (props.get("LootDropItemArray") or [])
    ]

    return {
        "id": obj["Name"],
        "items": items,
    }


def run_loot_drops(loot_drop_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCLootDropDataAsset files."""
    files = find_files(str(Path(loot_drop_dir) / "*.json"))
    print(f"  [loot_drops] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    drops = {}

    for f in files:
        result = extract_loot_drop(f)
        if not result:
            continue
        drop_id = result["id"]
        drops[drop_id] = result
        writer.write_entity("spawns", drop_id, result, source_files=[str(f)])
        index_entries.append({"id": drop_id})

    writer.write_index("spawns", index_entries)
    print(f"  [loot_drops] Extracted {len(drops)} loot drops")
    return drops
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/spawns/test_extract_loot_drops.py -v
```
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/spawns/extract_loot_drops.py tests/domains/spawns/test_extract_loot_drops.py
git commit -m "feat: add extract_loot_drops extractor"
```

---

## Chunk 2: LootDropGroups + LootDropRates + Orchestrator + Integration Test

### File Map

- Create: `pipeline/domains/spawns/extract_loot_drop_groups.py`
- Create: `pipeline/domains/spawns/extract_loot_drop_rates.py`
- Modify: `pipeline/domains/spawns/__init__.py` (full orchestrator)
- Create: `tests/domains/spawns/test_extract_loot_drop_groups.py`
- Create: `tests/domains/spawns/test_extract_loot_drop_rates.py`
- Create: `tests/domains/spawns/test_spawns_integration.py`

---

### Task 4: extract_loot_drop_groups.py — DCLootDropGroupDataAsset

**Files:**
- Create: `pipeline/domains/spawns/extract_loot_drop_groups.py`
- Create: `tests/domains/spawns/test_extract_loot_drop_groups.py`

- [ ] **Step 1: Write the failing tests**

`tests/domains/spawns/test_extract_loot_drop_groups.py`:
```python
"""Tests for pipeline/domains/spawns/extract_loot_drop_groups.py"""
import json
from pathlib import Path
from pipeline.domains.spawns.extract_loot_drop_groups import extract_loot_drop_group, run_loot_drop_groups


def make_loot_drop_group_file(tmp_path, group_id):
    data = [{
        "Type": "DCLootDropGroupDataAsset",
        "Name": group_id,
        "Properties": {
            "LootDropGroupItemArray": [
                {
                    "DungeonGrade": 2,
                    "LootDropId": {
                        "AssetPathName": "/Game/.../ID_Lootdrop_Swords.ID_Lootdrop_Swords",
                        "SubPathString": ""},
                    "LootDropRateId": {
                        "AssetPathName": "/Game/.../LDR_Common.LDR_Common",
                        "SubPathString": ""},
                    "LootDropCount": 3,
                }
            ]
        }
    }]
    f = tmp_path / f"{group_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_loot_drop_group_returns_id_and_items(tmp_path):
    f = make_loot_drop_group_file(tmp_path, "LDG_WeaponBundle")
    result = extract_loot_drop_group(f)
    assert result is not None
    assert result["id"] == "LDG_WeaponBundle"
    assert isinstance(result["items"], list)
    assert len(result["items"]) == 1
    item = result["items"][0]
    assert item["dungeon_grade"] == 2
    assert item["loot_drop_id"] == "ID_Lootdrop_Swords"
    assert item["loot_drop_rate_id"] == "LDR_Common"
    assert item["loot_drop_count"] == 3


def test_extract_loot_drop_group_handles_empty_items(tmp_path):
    data = [{"Type": "DCLootDropGroupDataAsset", "Name": "LDG_Empty",
             "Properties": {"LootDropGroupItemArray": []}}]
    f = tmp_path / "empty.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    result = extract_loot_drop_group(f)
    assert result is not None
    assert result["items"] == []


def test_extract_loot_drop_group_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_loot_drop_group(f) is None


def test_run_loot_drop_groups_writes_entity_and_index(tmp_path):
    groups_dir = tmp_path / "groups"
    groups_dir.mkdir()
    make_loot_drop_group_file(groups_dir, "LDG_WeaponBundle")
    extracted = tmp_path / "extracted"
    result = run_loot_drop_groups(loot_drop_group_dir=groups_dir, extracted_root=extracted)
    entity = extracted / "spawns" / "LDG_WeaponBundle.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id"] == "LDG_WeaponBundle"
    assert len(data["items"]) == 1
    assert "_meta" in data
    index = extracted / "spawns" / "_index.json"
    assert index.exists()
    assert "LDG_WeaponBundle" in result
```

- [ ] **Step 2: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/spawns/test_extract_loot_drop_groups.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement pipeline/domains/spawns/extract_loot_drop_groups.py**

```python
"""Extract DCLootDropGroupDataAsset files → extracted/spawns/<id>.json + _index.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.writer import Writer


def _extract_asset_id(ref: dict) -> str | None:
    """Extract asset ID from {"AssetPathName": "/Game/.../Foo.Foo", "SubPathString": ""}."""
    if not isinstance(ref, dict):
        return None
    asset_path = ref.get("AssetPathName", "")
    if not asset_path:
        return None
    parts = asset_path.split(".")
    return parts[-1] if len(parts) > 1 else None


def extract_loot_drop_group(file_path: Path) -> dict | None:
    """Extract one DCLootDropGroupDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError):
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCLootDropGroupDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    items = [
        {
            "dungeon_grade": item.get("DungeonGrade"),
            "loot_drop_id": _extract_asset_id(item.get("LootDropId")),
            "loot_drop_rate_id": _extract_asset_id(item.get("LootDropRateId")),
            "loot_drop_count": item.get("LootDropCount"),
        }
        for item in (props.get("LootDropGroupItemArray") or [])
    ]

    return {
        "id": obj["Name"],
        "items": items,
    }


def run_loot_drop_groups(loot_drop_group_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCLootDropGroupDataAsset files."""
    files = find_files(str(Path(loot_drop_group_dir) / "*.json"))
    print(f"  [loot_drop_groups] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    groups = {}

    for f in files:
        result = extract_loot_drop_group(f)
        if not result:
            continue
        group_id = result["id"]
        groups[group_id] = result
        writer.write_entity("spawns", group_id, result, source_files=[str(f)])
        index_entries.append({"id": group_id})

    writer.write_index("spawns", index_entries)
    print(f"  [loot_drop_groups] Extracted {len(groups)} loot drop groups")
    return groups
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/spawns/test_extract_loot_drop_groups.py -v
```
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/spawns/extract_loot_drop_groups.py tests/domains/spawns/test_extract_loot_drop_groups.py
git commit -m "feat: add extract_loot_drop_groups extractor"
```

---

### Task 5: extract_loot_drop_rates.py — DCLootDropRateDataAsset

**Files:**
- Create: `pipeline/domains/spawns/extract_loot_drop_rates.py`
- Create: `tests/domains/spawns/test_extract_loot_drop_rates.py`

- [ ] **Step 1: Write the failing tests**

`tests/domains/spawns/test_extract_loot_drop_rates.py`:
```python
"""Tests for pipeline/domains/spawns/extract_loot_drop_rates.py"""
import json
from pathlib import Path
from pipeline.domains.spawns.extract_loot_drop_rates import extract_loot_drop_rate, run_loot_drop_rates


def make_loot_drop_rate_file(tmp_path, rate_id):
    data = [{
        "Type": "DCLootDropRateDataAsset",
        "Name": rate_id,
        "Properties": {
            "LootDropRateItemArray": [
                {"LuckGrade": 1, "DropRate": 0.5},
                {"LuckGrade": 2, "DropRate": 0.3},
                {"LuckGrade": 3, "DropRate": 0.2},
            ]
        }
    }]
    f = tmp_path / f"{rate_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_loot_drop_rate_returns_id_and_rates(tmp_path):
    f = make_loot_drop_rate_file(tmp_path, "LDR_Common")
    result = extract_loot_drop_rate(f)
    assert result is not None
    assert result["id"] == "LDR_Common"
    assert isinstance(result["rates"], list)
    assert len(result["rates"]) == 3
    rate = result["rates"][0]
    assert rate["luck_grade"] == 1
    assert rate["drop_rate"] == 0.5


def test_extract_loot_drop_rate_handles_empty_rates(tmp_path):
    data = [{"Type": "DCLootDropRateDataAsset", "Name": "LDR_Empty",
             "Properties": {"LootDropRateItemArray": []}}]
    f = tmp_path / "empty.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    result = extract_loot_drop_rate(f)
    assert result is not None
    assert result["rates"] == []


def test_extract_loot_drop_rate_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_loot_drop_rate(f) is None


def test_run_loot_drop_rates_writes_entity_and_index(tmp_path):
    rates_dir = tmp_path / "rates"
    rates_dir.mkdir()
    make_loot_drop_rate_file(rates_dir, "LDR_Common")
    extracted = tmp_path / "extracted"
    result = run_loot_drop_rates(loot_drop_rate_dir=rates_dir, extracted_root=extracted)
    entity = extracted / "spawns" / "LDR_Common.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id"] == "LDR_Common"
    assert len(data["rates"]) == 3
    assert "_meta" in data
    index = extracted / "spawns" / "_index.json"
    assert index.exists()
    assert "LDR_Common" in result
```

- [ ] **Step 2: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/spawns/test_extract_loot_drop_rates.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement pipeline/domains/spawns/extract_loot_drop_rates.py**

```python
"""Extract DCLootDropRateDataAsset files → extracted/spawns/<id>.json + _index.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.writer import Writer


def extract_loot_drop_rate(file_path: Path) -> dict | None:
    """Extract one DCLootDropRateDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError):
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCLootDropRateDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    rates = [
        {
            "luck_grade": item.get("LuckGrade"),
            "drop_rate": item.get("DropRate"),
        }
        for item in (props.get("LootDropRateItemArray") or [])
    ]

    return {
        "id": obj["Name"],
        "rates": rates,
    }


def run_loot_drop_rates(loot_drop_rate_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCLootDropRateDataAsset files."""
    files = find_files(str(Path(loot_drop_rate_dir) / "*.json"))
    print(f"  [loot_drop_rates] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    rates = {}

    for f in files:
        result = extract_loot_drop_rate(f)
        if not result:
            continue
        rate_id = result["id"]
        rates[rate_id] = result
        writer.write_entity("spawns", rate_id, result, source_files=[str(f)])
        index_entries.append({"id": rate_id})

    writer.write_index("spawns", index_entries)
    print(f"  [loot_drop_rates] Extracted {len(rates)} loot drop rates")
    return rates
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/spawns/test_extract_loot_drop_rates.py -v
```
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/spawns/extract_loot_drop_rates.py tests/domains/spawns/test_extract_loot_drop_rates.py
git commit -m "feat: add extract_loot_drop_rates extractor"
```

---

### Task 6: spawns/__init__.py — orchestrator

**Files:**
- Modify: `pipeline/domains/spawns/__init__.py`

- [ ] **Step 1: Replace the stub with the full orchestrator**

`pipeline/domains/spawns/__init__.py`:
```python
"""Spawns domain extractor — run() called by extract_all.py orchestrator."""
from pathlib import Path

from pipeline.domains.spawns.extract_spawners import run_spawners
from pipeline.domains.spawns.extract_loot_drops import run_loot_drops
from pipeline.domains.spawns.extract_loot_drop_groups import run_loot_drop_groups
from pipeline.domains.spawns.extract_loot_drop_rates import run_loot_drop_rates
from pipeline.core.writer import Writer

_V2_BASE = "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2"


def run(raw_root: Path, extracted_root: Path) -> dict:
    """Run all spawns domain extractors. Returns summary of counts."""
    print("[spawns] Starting extraction...")
    summary = {}
    all_entities: dict[str, dict] = {}

    dirs = {
        "spawner":           raw_root / _V2_BASE / "Spawner" / "Spawner",
        "loot_drop":         raw_root / _V2_BASE / "LootDrop" / "LootDrop",
        "loot_drop_group":   raw_root / _V2_BASE / "LootDrop" / "LootDropGroup",
        "loot_drop_rate":    raw_root / _V2_BASE / "LootDrop" / "LootDropRate",
    }

    for key, fn, dir_key, entity_type, param in [
        ("spawners",          run_spawners,          "spawner",         "spawner",          "spawner_dir"),
        ("loot_drops",        run_loot_drops,        "loot_drop",       "loot_drop",        "loot_drop_dir"),
        ("loot_drop_groups",  run_loot_drop_groups,  "loot_drop_group", "loot_drop_group",  "loot_drop_group_dir"),
        ("loot_drop_rates",   run_loot_drop_rates,   "loot_drop_rate",  "loot_drop_rate",   "loot_drop_rate_dir"),
    ]:
        d = dirs[dir_key]
        if d.exists():
            entities = fn(**{param: d, "extracted_root": extracted_root})
            summary[key] = len(entities)
            all_entities.update({k: {**v, "_entity_type": entity_type}
                                  for k, v in entities.items()})
        else:
            print(f"  [spawns] WARNING: {d} not found")
            summary[key] = 0

    # Write combined index (overwrites partial indexes from individual run_* calls)
    combined_index = [
        {"id": v["id"], "type": v["_entity_type"]}
        for v in all_entities.values()
    ]
    Writer(extracted_root).write_index("spawns", combined_index)

    print(f"[spawns] Done. Summary: {summary}")
    return summary
```

- [ ] **Step 2: Run full spawns test suite to verify nothing broke**

```bash
py -3 -m pytest tests/domains/spawns/ -v --ignore=tests/domains/spawns/test_spawns_integration.py
```
Expected: All PASSED

- [ ] **Step 3: Commit**

```bash
git add pipeline/domains/spawns/__init__.py
git commit -m "feat: complete spawns orchestrator in __init__.py"
```

---

### Task 7: Integration test + full suite verification

**Files:**
- Create: `tests/domains/spawns/test_spawns_integration.py`

- [ ] **Step 1: Create the integration test**

`tests/domains/spawns/test_spawns_integration.py`:
```python
"""Integration test: run spawns domain against real raw data."""
import json
from pathlib import Path
import pytest
from pipeline.domains.spawns import run

RAW_ROOT = Path("raw")
SPAWNER_DIR = RAW_ROOT / "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/Spawner/Spawner"


@pytest.mark.skipif(not SPAWNER_DIR.exists(), reason="raw data not present")
def test_spawns_run_integration(tmp_path):
    summary = run(raw_root=RAW_ROOT, extracted_root=tmp_path)
    assert summary.get("spawners", 0) > 400
    assert summary.get("loot_drops", 0) > 2000
    assert summary.get("loot_drop_groups", 0) > 300
    assert summary.get("loot_drop_rates", 0) > 2000
    index = tmp_path / "spawns" / "_index.json"
    assert index.exists()
    index_data = json.loads(index.read_text(encoding="utf-8"))
    entity_types = {e["type"] for e in index_data["entries"]}
    assert "spawner" in entity_types
    assert "loot_drop" in entity_types
    assert "loot_drop_group" in entity_types
    assert "loot_drop_rate" in entity_types
```

- [ ] **Step 2: Run full test suite to verify all tests pass**

```bash
py -3 -m pytest tests/ -v --tb=short 2>&1 | tail -20
```
Expected: All prior tests + all new spawns tests PASSED (integration test skipped if no raw data)

- [ ] **Step 3: Commit**

```bash
git add tests/domains/spawns/test_spawns_integration.py
git commit -m "test: add spawns integration test"
```

---

## Final verification

- [ ] **Run the complete test suite one final time**

```bash
py -3 -m pytest tests/ --tb=short 2>&1 | tail -5
```
Expected: All tests passed, 0 failures
