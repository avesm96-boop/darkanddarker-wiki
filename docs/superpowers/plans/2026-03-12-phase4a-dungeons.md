# Phase 4a: Dungeons Domain Extractor Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `pipeline/domains/dungeons/` with 13 sub-extractors producing `extracted/dungeons/<id>.json` entity files and a combined `_index.json`.

**Architecture:** Each sub-extractor is a focused module with one `extract_*()` function and one `run_*()` function. `extract_floor_rules.py` and `extract_vehicles.py` each handle 3 related asset types in one file. `__init__.py` orchestrates all sub-extractors and writes a single combined index following the exact pattern of `pipeline/domains/combat/__init__.py`.

**Tech Stack:** Python 3.10+, pytest, pathlib, pipeline.core (reader, writer, normalizer)

**Spec:** `docs/superpowers/specs/2026-03-12-phase4-dungeons-spawns-design.md` §2.1, §3, §4.1, §5.1, §6, §7, §8

---

## Chunk 1: Test Infrastructure + extract_dungeons.py

### File Map

- Create: `pipeline/domains/dungeons/__init__.py`
- Create: `pipeline/domains/dungeons/extract_dungeons.py`
- Create: `tests/domains/dungeons/__init__.py`
- Create: `tests/domains/dungeons/test_extract_dungeons.py`

---

### Task 1: Test infrastructure

**Files:**
- Create: `pipeline/domains/dungeons/__init__.py` (empty stub)
- Create: `tests/domains/dungeons/__init__.py` (empty)

- [ ] **Step 1: Create the two empty `__init__.py` files**

`pipeline/domains/dungeons/__init__.py`:
```python
"""Dungeons domain extractor — run() called by extract_all.py orchestrator."""
```

`tests/domains/dungeons/__init__.py`:
```python
```
(empty file)

- [ ] **Step 2: Verify pytest can collect from the new directory**

Run from `darkanddarker-wiki/`:
```bash
py -3 -m pytest tests/domains/dungeons/ --collect-only
```
Expected: `no tests ran` (directory exists, no test files yet)

---

### Task 2: extract_dungeons.py — DCDungeonDataAsset

**Files:**
- Create: `pipeline/domains/dungeons/extract_dungeons.py`
- Create: `tests/domains/dungeons/test_extract_dungeons.py`

- [ ] **Step 1: Write the failing tests**

`tests/domains/dungeons/test_extract_dungeons.py`:
```python
"""Tests for pipeline/domains/dungeons/extract_dungeons.py"""
import json
from pathlib import Path
from pipeline.domains.dungeons.extract_dungeons import extract_dungeon, run_dungeons


def make_dungeon_file(tmp_path, dungeon_id):
    data = [{
        "Type": "DCDungeonDataAsset",
        "Name": dungeon_id,
        "Properties": {
            "IdTag": {"TagName": "Dungeon.Crypts"},
            "Name": {"LocalizedString": "Crypts"},
            "GameTypes": ["EGameType::Normal"],
            "DefaultDungeonGrade": 2,
            "floor": 1,
            "FloorRule": {"AssetPathName": "/Game/.../FR_Crypts.FR_Crypts", "SubPathString": ""},
            "TriumphExp": 100,
            "ModuleType": "EDCDungeonModuleType::Standard",
            "bFogEnabled": True,
            "NumMinEscapes": 3,
        }
    }]
    f = tmp_path / f"{dungeon_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_dungeon_returns_id_and_fields(tmp_path):
    f = make_dungeon_file(tmp_path, "Id_Dungeon_Crypts_A")
    result = extract_dungeon(f)
    assert result is not None
    assert result["id"] == "Id_Dungeon_Crypts_A"
    assert result["id_tag"] == "Dungeon.Crypts"
    assert result["name"] == "Crypts"
    assert result["game_types"] == ["EGameType::Normal"]
    assert result["default_dungeon_grade"] == 2
    assert result["floor"] == 1
    assert result["floor_rule"] == "FR_Crypts"
    assert result["triumph_exp"] == 100
    assert result["module_type"] == "EDCDungeonModuleType::Standard"
    assert result["fog_enabled"] is True
    assert result["num_min_escapes"] == 3


def test_extract_dungeon_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_dungeon(f) is None


def test_run_dungeons_writes_entity_and_index(tmp_path):
    dungeon_dir = tmp_path / "dungeon"
    dungeon_dir.mkdir()
    make_dungeon_file(dungeon_dir, "Id_Dungeon_Crypts_A")
    extracted = tmp_path / "extracted"
    result = run_dungeons(dungeon_dir=dungeon_dir, extracted_root=extracted)
    entity = extracted / "dungeons" / "Id_Dungeon_Crypts_A.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id"] == "Id_Dungeon_Crypts_A"
    assert data["id_tag"] == "Dungeon.Crypts"
    assert "_meta" in data
    index = extracted / "dungeons" / "_index.json"
    assert index.exists()
    assert "Id_Dungeon_Crypts_A" in result
```

- [ ] **Step 2: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/dungeons/test_extract_dungeons.py -v
```
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement pipeline/domains/dungeons/extract_dungeons.py**

```python
"""Extract DCDungeonDataAsset files → extracted/dungeons/<id>.json + _index.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_tag, resolve_text
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


def extract_dungeon(file_path: Path) -> dict | None:
    """Extract one DCDungeonDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError):
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCDungeonDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    return {
        "id": obj["Name"],
        "id_tag": resolve_tag(props.get("IdTag")),
        "name": resolve_text(props.get("Name")),
        "game_types": props.get("GameTypes") or [],
        "default_dungeon_grade": props.get("DefaultDungeonGrade"),
        "floor": props.get("floor"),
        "floor_rule": _extract_asset_id(props.get("FloorRule")),
        "triumph_exp": props.get("TriumphExp"),
        "module_type": props.get("ModuleType"),
        "fog_enabled": props.get("bFogEnabled"),
        "num_min_escapes": props.get("NumMinEscapes"),
    }


def run_dungeons(dungeon_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCDungeonDataAsset files."""
    files = find_files(str(Path(dungeon_dir) / "*.json"))
    print(f"  [dungeons] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    dungeons = {}

    for f in files:
        result = extract_dungeon(f)
        if not result:
            continue
        dungeon_id = result["id"]
        dungeons[dungeon_id] = result
        writer.write_entity("dungeons", dungeon_id, result, source_files=[str(f)])
        index_entries.append({"id": dungeon_id})

    writer.write_index("dungeons", index_entries)
    print(f"  [dungeons] Extracted {len(dungeons)} dungeons")
    return dungeons
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/dungeons/test_extract_dungeons.py -v
```
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/dungeons/__init__.py pipeline/domains/dungeons/extract_dungeons.py tests/domains/dungeons/__init__.py tests/domains/dungeons/test_extract_dungeons.py
git commit -m "feat: add dungeons domain + extract_dungeons extractor"
```

---

## Chunk 2: DungeonType, DungeonGrade, DungeonCard

### File Map

- Create: `pipeline/domains/dungeons/extract_dungeon_types.py`
- Create: `pipeline/domains/dungeons/extract_dungeon_grades.py`
- Create: `pipeline/domains/dungeons/extract_dungeon_cards.py`
- Create: `tests/domains/dungeons/test_extract_dungeon_types.py`
- Create: `tests/domains/dungeons/test_extract_dungeon_grades.py`
- Create: `tests/domains/dungeons/test_extract_dungeon_cards.py`

---

### Task 3: extract_dungeon_types.py — DCDungeonTypeDataAsset

**Files:**
- Create: `pipeline/domains/dungeons/extract_dungeon_types.py`
- Create: `tests/domains/dungeons/test_extract_dungeon_types.py`

- [ ] **Step 1: Write the failing tests**

`tests/domains/dungeons/test_extract_dungeon_types.py`:
```python
"""Tests for pipeline/domains/dungeons/extract_dungeon_types.py"""
import json
from pathlib import Path
from pipeline.domains.dungeons.extract_dungeon_types import extract_dungeon_type, run_dungeon_types


def make_dungeon_type_file(tmp_path, type_id):
    data = [{
        "Type": "DCDungeonTypeDataAsset",
        "Name": type_id,
        "Properties": {
            "IdTag": {"TagName": "DungeonType.Crypts"},
            "Name": {"LocalizedString": "Crypts"},
            "GroupName": {"LocalizedString": "Underground"},
            "ChapterName": {"LocalizedString": "Chapter 1"},
            "Desc": {"LocalizedString": "Dark underground dungeons"},
            "Order": 1,
        }
    }]
    f = tmp_path / f"{type_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_dungeon_type_returns_id_and_fields(tmp_path):
    f = make_dungeon_type_file(tmp_path, "Id_DungeonType_Crypts")
    result = extract_dungeon_type(f)
    assert result is not None
    assert result["id"] == "Id_DungeonType_Crypts"
    assert result["id_tag"] == "DungeonType.Crypts"
    assert result["name"] == "Crypts"
    assert result["group_name"] == "Underground"
    assert result["chapter_name"] == "Chapter 1"
    assert result["desc"] == "Dark underground dungeons"
    assert result["order"] == 1


def test_extract_dungeon_type_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_dungeon_type(f) is None


def test_run_dungeon_types_writes_entity_and_index(tmp_path):
    type_dir = tmp_path / "dungeon_type"
    type_dir.mkdir()
    make_dungeon_type_file(type_dir, "Id_DungeonType_Crypts")
    extracted = tmp_path / "extracted"
    result = run_dungeon_types(dungeon_type_dir=type_dir, extracted_root=extracted)
    entity = extracted / "dungeons" / "Id_DungeonType_Crypts.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id_tag"] == "DungeonType.Crypts"
    assert "_meta" in data
    index = extracted / "dungeons" / "_index.json"
    assert index.exists()
    assert "Id_DungeonType_Crypts" in result
```

- [ ] **Step 2: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/dungeons/test_extract_dungeon_types.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement pipeline/domains/dungeons/extract_dungeon_types.py**

```python
"""Extract DCDungeonTypeDataAsset files → extracted/dungeons/<id>.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_tag, resolve_text
from pipeline.core.writer import Writer


def extract_dungeon_type(file_path: Path) -> dict | None:
    """Extract one DCDungeonTypeDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError):
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCDungeonTypeDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    return {
        "id": obj["Name"],
        "id_tag": resolve_tag(props.get("IdTag")),
        "name": resolve_text(props.get("Name")),
        "group_name": resolve_text(props.get("GroupName")),
        "chapter_name": resolve_text(props.get("ChapterName")),
        "desc": resolve_text(props.get("Desc")),
        "order": props.get("Order"),
    }


def run_dungeon_types(dungeon_type_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCDungeonTypeDataAsset files."""
    files = find_files(str(Path(dungeon_type_dir) / "*.json"))
    print(f"  [dungeon_types] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    types = {}

    for f in files:
        result = extract_dungeon_type(f)
        if not result:
            continue
        type_id = result["id"]
        types[type_id] = result
        writer.write_entity("dungeons", type_id, result, source_files=[str(f)])
        index_entries.append({"id": type_id})

    writer.write_index("dungeons", index_entries)
    print(f"  [dungeon_types] Extracted {len(types)} dungeon types")
    return types
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/dungeons/test_extract_dungeon_types.py -v
```
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/dungeons/extract_dungeon_types.py tests/domains/dungeons/test_extract_dungeon_types.py
git commit -m "feat: add extract_dungeon_types extractor"
```

---

### Task 4: extract_dungeon_grades.py — DCDungeonGradeDataAsset

**Files:**
- Create: `pipeline/domains/dungeons/extract_dungeon_grades.py`
- Create: `tests/domains/dungeons/test_extract_dungeon_grades.py`

NOTE: Field is `DungeonIdTag` (not `IdTag`). `.get()` used intentionally — some records omit this.

- [ ] **Step 1: Write the failing tests**

`tests/domains/dungeons/test_extract_dungeon_grades.py`:
```python
"""Tests for pipeline/domains/dungeons/extract_dungeon_grades.py"""
import json
from pathlib import Path
from pipeline.domains.dungeons.extract_dungeon_grades import extract_dungeon_grade, run_dungeon_grades


def make_dungeon_grade_file(tmp_path, grade_id):
    data = [{
        "Type": "DCDungeonGradeDataAsset",
        "Name": grade_id,
        "Properties": {
            "DungeonIdTag": {"TagName": "DungeonGrade.Normal"},
            "GearPoolIndex": 3,
        }
    }]
    f = tmp_path / f"{grade_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_dungeon_grade_returns_id_and_fields(tmp_path):
    f = make_dungeon_grade_file(tmp_path, "Id_DungeonGrade_Normal")
    result = extract_dungeon_grade(f)
    assert result is not None
    assert result["id"] == "Id_DungeonGrade_Normal"
    assert result["dungeon_id_tag"] == "DungeonGrade.Normal"
    assert result["gear_pool_index"] == 3


def test_extract_dungeon_grade_handles_missing_id_tag(tmp_path):
    data = [{"Type": "DCDungeonGradeDataAsset", "Name": "Id_DungeonGrade_NoTag",
             "Properties": {"GearPoolIndex": 1}}]
    f = tmp_path / "grade.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    result = extract_dungeon_grade(f)
    assert result is not None
    assert result["dungeon_id_tag"] is None
    assert result["gear_pool_index"] == 1


def test_extract_dungeon_grade_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_dungeon_grade(f) is None


def test_run_dungeon_grades_writes_entity_and_index(tmp_path):
    grade_dir = tmp_path / "grades"
    grade_dir.mkdir()
    make_dungeon_grade_file(grade_dir, "Id_DungeonGrade_Normal")
    extracted = tmp_path / "extracted"
    result = run_dungeon_grades(dungeon_grade_dir=grade_dir, extracted_root=extracted)
    entity = extracted / "dungeons" / "Id_DungeonGrade_Normal.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["dungeon_id_tag"] == "DungeonGrade.Normal"
    assert "_meta" in data
    assert "Id_DungeonGrade_Normal" in result
```

- [ ] **Step 2: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/dungeons/test_extract_dungeon_grades.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement pipeline/domains/dungeons/extract_dungeon_grades.py**

```python
"""Extract DCDungeonGradeDataAsset files → extracted/dungeons/<id>.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_tag
from pipeline.core.writer import Writer


def extract_dungeon_grade(file_path: Path) -> dict | None:
    """Extract one DCDungeonGradeDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError):
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCDungeonGradeDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    return {
        "id": obj["Name"],
        "dungeon_id_tag": resolve_tag(props.get("DungeonIdTag")),
        "gear_pool_index": props.get("GearPoolIndex"),
    }


def run_dungeon_grades(dungeon_grade_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCDungeonGradeDataAsset files."""
    files = find_files(str(Path(dungeon_grade_dir) / "*.json"))
    print(f"  [dungeon_grades] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    grades = {}

    for f in files:
        result = extract_dungeon_grade(f)
        if not result:
            continue
        grade_id = result["id"]
        grades[grade_id] = result
        writer.write_entity("dungeons", grade_id, result, source_files=[str(f)])
        index_entries.append({"id": grade_id})

    writer.write_index("dungeons", index_entries)
    print(f"  [dungeon_grades] Extracted {len(grades)} dungeon grades")
    return grades
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/dungeons/test_extract_dungeon_grades.py -v
```
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/dungeons/extract_dungeon_grades.py tests/domains/dungeons/test_extract_dungeon_grades.py
git commit -m "feat: add extract_dungeon_grades extractor"
```

---

### Task 5: extract_dungeon_cards.py — DCDungeonCardDataAsset

**Files:**
- Create: `pipeline/domains/dungeons/extract_dungeon_cards.py`
- Create: `tests/domains/dungeons/test_extract_dungeon_cards.py`

NOTE: Source data has no `Properties` for dungeon cards — only `id` is extracted.

- [ ] **Step 1: Write the failing tests**

`tests/domains/dungeons/test_extract_dungeon_cards.py`:
```python
"""Tests for pipeline/domains/dungeons/extract_dungeon_cards.py"""
import json
from pathlib import Path
from pipeline.domains.dungeons.extract_dungeon_cards import extract_dungeon_card, run_dungeon_cards


def make_dungeon_card_file(tmp_path, card_id):
    data = [{"Type": "DCDungeonCardDataAsset", "Name": card_id}]
    f = tmp_path / f"{card_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_dungeon_card_returns_id(tmp_path):
    f = make_dungeon_card_file(tmp_path, "Id_DungeonCard_Trap")
    result = extract_dungeon_card(f)
    assert result is not None
    assert result["id"] == "Id_DungeonCard_Trap"


def test_extract_dungeon_card_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_dungeon_card(f) is None


def test_run_dungeon_cards_writes_entity_and_index(tmp_path):
    card_dir = tmp_path / "cards"
    card_dir.mkdir()
    make_dungeon_card_file(card_dir, "Id_DungeonCard_Trap")
    extracted = tmp_path / "extracted"
    result = run_dungeon_cards(dungeon_card_dir=card_dir, extracted_root=extracted)
    entity = extracted / "dungeons" / "Id_DungeonCard_Trap.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id"] == "Id_DungeonCard_Trap"
    assert "_meta" in data
    assert "Id_DungeonCard_Trap" in result
```

- [ ] **Step 2: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/dungeons/test_extract_dungeon_cards.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement pipeline/domains/dungeons/extract_dungeon_cards.py**

```python
"""Extract DCDungeonCardDataAsset files → extracted/dungeons/<id>.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files
from pipeline.core.writer import Writer


def extract_dungeon_card(file_path: Path) -> dict | None:
    """Extract one DCDungeonCardDataAsset file. Source data has no Properties."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError):
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCDungeonCardDataAsset"), None)
    if not obj:
        return None

    return {"id": obj["Name"]}


def run_dungeon_cards(dungeon_card_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCDungeonCardDataAsset files."""
    files = find_files(str(Path(dungeon_card_dir) / "*.json"))
    print(f"  [dungeon_cards] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    cards = {}

    for f in files:
        result = extract_dungeon_card(f)
        if not result:
            continue
        card_id = result["id"]
        cards[card_id] = result
        writer.write_entity("dungeons", card_id, result, source_files=[str(f)])
        index_entries.append({"id": card_id})

    writer.write_index("dungeons", index_entries)
    print(f"  [dungeon_cards] Extracted {len(cards)} dungeon cards")
    return cards
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/dungeons/test_extract_dungeon_cards.py -v
```
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/dungeons/extract_dungeon_cards.py tests/domains/dungeons/test_extract_dungeon_cards.py
git commit -m "feat: add extract_dungeon_cards extractor"
```

---

## Chunk 3: DungeonLayout, DungeonModule

### File Map

- Create: `pipeline/domains/dungeons/extract_dungeon_layouts.py`
- Create: `pipeline/domains/dungeons/extract_dungeon_modules.py`
- Create: `tests/domains/dungeons/test_extract_dungeon_layouts.py`
- Create: `tests/domains/dungeons/test_extract_dungeon_modules.py`

---

### Task 6: extract_dungeon_layouts.py — DCDungeonLayoutDataAsset

**Files:**
- Create: `pipeline/domains/dungeons/extract_dungeon_layouts.py`
- Create: `tests/domains/dungeons/test_extract_dungeon_layouts.py`

NOTE: `Slots` is a flat array; `Module` refs currently null in source data but `_extract_asset_id` used for forward-compatibility.

- [ ] **Step 1: Write the failing tests**

`tests/domains/dungeons/test_extract_dungeon_layouts.py`:
```python
"""Tests for pipeline/domains/dungeons/extract_dungeon_layouts.py"""
import json
from pathlib import Path
from pipeline.domains.dungeons.extract_dungeon_layouts import extract_dungeon_layout, run_dungeon_layouts


def make_dungeon_layout_file(tmp_path, layout_id):
    data = [{
        "Type": "DCDungeonLayoutDataAsset",
        "Name": layout_id,
        "Properties": {
            "Size": {"X": 2, "Y": 2},
            "Slots": [
                {
                    "SlotTypes": [
                        {
                            "SlotType": "EDCDungeonLayoutSlotType::Normal",
                            "Module": {"AssetPathName": "/Game/.../DM_A.DM_A", "SubPathString": ""},
                            "Rotation": "EDCDungeonModuleRotation::R0",
                        }
                    ]
                },
                {"SlotTypes": []},
                {"SlotTypes": []},
                {"SlotTypes": []},
            ]
        }
    }]
    f = tmp_path / f"{layout_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_dungeon_layout_returns_id_and_fields(tmp_path):
    f = make_dungeon_layout_file(tmp_path, "Id_DungeonLayout_Crypts_001")
    result = extract_dungeon_layout(f)
    assert result is not None
    assert result["id"] == "Id_DungeonLayout_Crypts_001"
    assert result["size_x"] == 2
    assert result["size_y"] == 2
    assert isinstance(result["slots"], list)
    assert len(result["slots"]) == 4
    first_slot = result["slots"][0]
    assert "slot_types" in first_slot
    assert len(first_slot["slot_types"]) == 1
    st = first_slot["slot_types"][0]
    assert st["slot_type"] == "EDCDungeonLayoutSlotType::Normal"
    assert st["module_id"] == "DM_A"
    assert st["rotation"] == "EDCDungeonModuleRotation::R0"


def test_extract_dungeon_layout_handles_null_module(tmp_path):
    data = [{
        "Type": "DCDungeonLayoutDataAsset",
        "Name": "Id_Layout_NoModule",
        "Properties": {
            "Size": {"X": 1, "Y": 1},
            "Slots": [{"SlotTypes": [{"SlotType": "EDCDungeonLayoutSlotType::Normal",
                                      "Module": None, "Rotation": "EDCDungeonModuleRotation::R0"}]}]
        }
    }]
    f = tmp_path / "layout.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    result = extract_dungeon_layout(f)
    assert result is not None
    assert result["slots"][0]["slot_types"][0]["module_id"] is None


def test_extract_dungeon_layout_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_dungeon_layout(f) is None


def test_run_dungeon_layouts_writes_entity_and_index(tmp_path):
    layout_dir = tmp_path / "layouts"
    layout_dir.mkdir()
    make_dungeon_layout_file(layout_dir, "Id_DungeonLayout_Crypts_001")
    extracted = tmp_path / "extracted"
    result = run_dungeon_layouts(dungeon_layout_dir=layout_dir, extracted_root=extracted)
    entity = extracted / "dungeons" / "Id_DungeonLayout_Crypts_001.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["size_x"] == 2
    assert "_meta" in data
    assert "Id_DungeonLayout_Crypts_001" in result
```

- [ ] **Step 2: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/dungeons/test_extract_dungeon_layouts.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement pipeline/domains/dungeons/extract_dungeon_layouts.py**

```python
"""Extract DCDungeonLayoutDataAsset files → extracted/dungeons/<id>.json."""
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


def extract_dungeon_layout(file_path: Path) -> dict | None:
    """Extract one DCDungeonLayoutDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError):
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCDungeonLayoutDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    size = props.get("Size") or {}
    slots = [
        {
            "slot_types": [
                {
                    "slot_type": st.get("SlotType"),
                    "module_id": _extract_asset_id(st.get("Module")),
                    "rotation": st.get("Rotation"),
                }
                for st in (slot.get("SlotTypes") or [])
            ]
        }
        for slot in (props.get("Slots") or [])
    ]

    return {
        "id": obj["Name"],
        "size_x": size.get("X"),
        "size_y": size.get("Y"),
        "slots": slots,
    }


def run_dungeon_layouts(dungeon_layout_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCDungeonLayoutDataAsset files."""
    files = find_files(str(Path(dungeon_layout_dir) / "*.json"))
    print(f"  [dungeon_layouts] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    layouts = {}

    for f in files:
        result = extract_dungeon_layout(f)
        if not result:
            continue
        layout_id = result["id"]
        layouts[layout_id] = result
        writer.write_entity("dungeons", layout_id, result, source_files=[str(f)])
        index_entries.append({"id": layout_id})

    writer.write_index("dungeons", index_entries)
    print(f"  [dungeon_layouts] Extracted {len(layouts)} dungeon layouts")
    return layouts
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/dungeons/test_extract_dungeon_layouts.py -v
```
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/dungeons/extract_dungeon_layouts.py tests/domains/dungeons/test_extract_dungeon_layouts.py
git commit -m "feat: add extract_dungeon_layouts extractor"
```

---

### Task 7: extract_dungeon_modules.py — DCDungeonModuleDataAsset

**Files:**
- Create: `pipeline/domains/dungeons/extract_dungeon_modules.py`
- Create: `tests/domains/dungeons/test_extract_dungeon_modules.py`

- [ ] **Step 1: Write the failing tests**

`tests/domains/dungeons/test_extract_dungeon_modules.py`:
```python
"""Tests for pipeline/domains/dungeons/extract_dungeon_modules.py"""
import json
from pathlib import Path
from pipeline.domains.dungeons.extract_dungeon_modules import extract_dungeon_module, run_dungeon_modules


def make_dungeon_module_file(tmp_path, module_id):
    data = [{
        "Type": "DCDungeonModuleDataAsset",
        "Name": module_id,
        "Properties": {
            "Name": {"LocalizedString": "Crypt Hall"},
            "ModuleType": "EDCDungeonModuleType::Standard",
            "Size": {"X": 3, "Y": 2},
        }
    }]
    f = tmp_path / f"{module_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_dungeon_module_returns_id_and_fields(tmp_path):
    f = make_dungeon_module_file(tmp_path, "Id_DungeonModule_CryptHall")
    result = extract_dungeon_module(f)
    assert result is not None
    assert result["id"] == "Id_DungeonModule_CryptHall"
    assert result["name"] == "Crypt Hall"
    assert result["module_type"] == "EDCDungeonModuleType::Standard"
    assert result["size_x"] == 3
    assert result["size_y"] == 2


def test_extract_dungeon_module_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_dungeon_module(f) is None


def test_run_dungeon_modules_writes_entity_and_index(tmp_path):
    module_dir = tmp_path / "modules"
    module_dir.mkdir()
    make_dungeon_module_file(module_dir, "Id_DungeonModule_CryptHall")
    extracted = tmp_path / "extracted"
    result = run_dungeon_modules(dungeon_module_dir=module_dir, extracted_root=extracted)
    entity = extracted / "dungeons" / "Id_DungeonModule_CryptHall.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["size_x"] == 3
    assert "_meta" in data
    assert "Id_DungeonModule_CryptHall" in result
```

- [ ] **Step 2: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/dungeons/test_extract_dungeon_modules.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement pipeline/domains/dungeons/extract_dungeon_modules.py**

```python
"""Extract DCDungeonModuleDataAsset files → extracted/dungeons/<id>.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_text
from pipeline.core.writer import Writer


def extract_dungeon_module(file_path: Path) -> dict | None:
    """Extract one DCDungeonModuleDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError):
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCDungeonModuleDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    size = props.get("Size") or {}
    return {
        "id": obj["Name"],
        "name": resolve_text(props.get("Name")),
        "module_type": props.get("ModuleType"),
        "size_x": size.get("X"),
        "size_y": size.get("Y"),
    }


def run_dungeon_modules(dungeon_module_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCDungeonModuleDataAsset files."""
    files = find_files(str(Path(dungeon_module_dir) / "*.json"))
    print(f"  [dungeon_modules] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    modules = {}

    for f in files:
        result = extract_dungeon_module(f)
        if not result:
            continue
        module_id = result["id"]
        modules[module_id] = result
        writer.write_entity("dungeons", module_id, result, source_files=[str(f)])
        index_entries.append({"id": module_id})

    writer.write_index("dungeons", index_entries)
    print(f"  [dungeon_modules] Extracted {len(modules)} dungeon modules")
    return modules
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/dungeons/test_extract_dungeon_modules.py -v
```
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/dungeons/extract_dungeon_modules.py tests/domains/dungeons/test_extract_dungeon_modules.py
git commit -m "feat: add extract_dungeon_modules extractor"
```

---

## Chunk 4: FloorRules + Props extractors

### File Map

- Create: `pipeline/domains/dungeons/extract_floor_rules.py`
- Create: `pipeline/domains/dungeons/extract_props.py`
- Create: `pipeline/domains/dungeons/extract_props_effects.py`
- Create: `pipeline/domains/dungeons/extract_props_interacts.py`
- Create: `pipeline/domains/dungeons/extract_props_skill_checks.py`
- Create: `tests/domains/dungeons/test_extract_floor_rules.py`
- Create: `tests/domains/dungeons/test_extract_props.py`
- Create: `tests/domains/dungeons/test_extract_props_effects.py`
- Create: `tests/domains/dungeons/test_extract_props_interacts.py`
- Create: `tests/domains/dungeons/test_extract_props_skill_checks.py`

---

### Task 8: extract_floor_rules.py — three asset types

**Files:**
- Create: `pipeline/domains/dungeons/extract_floor_rules.py`
- Create: `tests/domains/dungeons/test_extract_floor_rules.py`

NOTE: One file handles three types: `DCFloorPortalDataAsset`, `DCFloorRuleBlizzardDataAsset`, `DCFloorRuleDeathSwarmDataAsset`. The `run_floor_rules()` function tags entities with `_entity_type`.

- [ ] **Step 1: Write the failing tests**

`tests/domains/dungeons/test_extract_floor_rules.py`:
```python
"""Tests for pipeline/domains/dungeons/extract_floor_rules.py"""
import json
from pathlib import Path
from pipeline.domains.dungeons.extract_floor_rules import (
    extract_floor_portal, extract_floor_rule_blizzard, extract_floor_rule_deathswarm,
    run_floor_rules,
)


def make_file(tmp_path, subdir, filename, data):
    d = tmp_path / subdir
    d.mkdir(parents=True, exist_ok=True)
    f = d / filename
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_floor_portal_returns_fields(tmp_path):
    f = make_file(tmp_path, "FloorPortal", "Id_FloorPortal_A.json", [{
        "Type": "DCFloorPortalDataAsset",
        "Name": "Id_FloorPortal_A",
        "Properties": {"PortalType": "EPortalType::Normal", "PortalScrollNum": 2}
    }])
    result = extract_floor_portal(f)
    assert result is not None
    assert result["id"] == "Id_FloorPortal_A"
    assert result["portal_type"] == "EPortalType::Normal"
    assert result["portal_scroll_num"] == 2


def test_extract_floor_portal_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_floor_portal(f) is None


def test_extract_floor_rule_blizzard_returns_id(tmp_path):
    f = tmp_path / "blizzard.json"
    f.write_text('[{"Type": "DCFloorRuleBlizzardDataAsset", "Name": "Id_Blizzard_A"}]',
                 encoding="utf-8")
    result = extract_floor_rule_blizzard(f)
    assert result is not None
    assert result["id"] == "Id_Blizzard_A"


def test_extract_floor_rule_blizzard_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_floor_rule_blizzard(f) is None


def test_extract_floor_rule_deathswarm_returns_fields(tmp_path):
    data = [{"Type": "DCFloorRuleDeathSwarmDataAsset", "Name": "Id_DeathSwarm_A",
             "Properties": {"FloorRuleItemArray": [{"item": 1}]}}]
    f = tmp_path / "deathswarm.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    result = extract_floor_rule_deathswarm(f)
    assert result is not None
    assert result["id"] == "Id_DeathSwarm_A"
    assert result["floor_rule_items"] == [{"item": 1}]


def test_extract_floor_rule_deathswarm_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_floor_rule_deathswarm(f) is None


def test_run_floor_rules_writes_entities_and_combined_index(tmp_path):
    floor_rule_dir = tmp_path / "FloorRule"
    make_file(floor_rule_dir, "FloorPortal", "Id_FloorPortal_A.json", [{
        "Type": "DCFloorPortalDataAsset", "Name": "Id_FloorPortal_A",
        "Properties": {"PortalType": "EPortalType::Normal", "PortalScrollNum": 1}
    }])
    make_file(floor_rule_dir, "FloorRuleBlizzard", "Id_Blizzard_A.json", [
        {"Type": "DCFloorRuleBlizzardDataAsset", "Name": "Id_Blizzard_A"}
    ])
    make_file(floor_rule_dir, "FloorRuleDeathSwarm", "Id_DeathSwarm_A.json", [{
        "Type": "DCFloorRuleDeathSwarmDataAsset", "Name": "Id_DeathSwarm_A",
        "Properties": {"FloorRuleItemArray": []}
    }])
    extracted = tmp_path / "extracted"
    result = run_floor_rules(floor_rule_dir=floor_rule_dir, extracted_root=extracted)
    assert "Id_FloorPortal_A" in result
    assert "Id_Blizzard_A" in result
    assert "Id_DeathSwarm_A" in result
    assert result["Id_FloorPortal_A"]["_entity_type"] == "floor_portal"
    assert result["Id_Blizzard_A"]["_entity_type"] == "floor_rule_blizzard"
    assert result["Id_DeathSwarm_A"]["_entity_type"] == "floor_rule_deathswarm"
    portal_file = extracted / "dungeons" / "Id_FloorPortal_A.json"
    assert portal_file.exists()
```

- [ ] **Step 2: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/dungeons/test_extract_floor_rules.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement pipeline/domains/dungeons/extract_floor_rules.py**

```python
"""Extract floor rule assets → extracted/dungeons/<id>.json.

Handles three types in one file:
  DCFloorPortalDataAsset      → FloorRule/FloorPortal/
  DCFloorRuleBlizzardDataAsset → FloorRule/FloorRuleBlizzard/
  DCFloorRuleDeathSwarmDataAsset → FloorRule/FloorRuleDeathSwarm/
"""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.writer import Writer


def extract_floor_portal(file_path: Path) -> dict | None:
    """Extract one DCFloorPortalDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError):
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCFloorPortalDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    return {
        "id": obj["Name"],
        "portal_type": props.get("PortalType"),
        "portal_scroll_num": props.get("PortalScrollNum"),
    }


def extract_floor_rule_blizzard(file_path: Path) -> dict | None:
    """Extract one DCFloorRuleBlizzardDataAsset file. Minimal/no properties in source data."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError):
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCFloorRuleBlizzardDataAsset"), None)
    if not obj:
        return None

    return {"id": obj["Name"]}


def extract_floor_rule_deathswarm(file_path: Path) -> dict | None:
    """Extract one DCFloorRuleDeathSwarmDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError):
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCFloorRuleDeathSwarmDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    return {
        "id": obj["Name"],
        "floor_rule_items": props.get("FloorRuleItemArray") or [],
    }


def run_floor_rules(floor_rule_dir: Path, extracted_root: Path) -> dict:
    """Extract all floor rule assets from sub-directories.

    Scans FloorPortal/, FloorRuleBlizzard/, FloorRuleDeathSwarm/ under floor_rule_dir.
    Tags each entity with _entity_type. Returns combined {id: entity} dict.
    """
    floor_rule_dir = Path(floor_rule_dir)
    writer = Writer(extracted_root)
    all_rules = {}

    extractors = [
        ("FloorPortal", extract_floor_portal, "floor_portal"),
        ("FloorRuleBlizzard", extract_floor_rule_blizzard, "floor_rule_blizzard"),
        ("FloorRuleDeathSwarm", extract_floor_rule_deathswarm, "floor_rule_deathswarm"),
    ]

    for subdir, extractor, entity_type in extractors:
        subdir_path = floor_rule_dir / subdir
        if not subdir_path.exists():
            print(f"  [floor_rules] WARNING: {subdir_path} not found")
            continue
        files = find_files(str(subdir_path / "*.json"))
        print(f"  [floor_rules/{subdir}] Found {len(files)} files")
        for f in files:
            result = extractor(f)
            if not result:
                continue
            rule_id = result["id"]
            tagged = {**result, "_entity_type": entity_type}
            all_rules[rule_id] = tagged
            writer.write_entity("dungeons", rule_id, result, source_files=[str(f)])

    writer.write_index("dungeons", [{"id": v["id"]} for v in all_rules.values()])
    print(f"  [floor_rules] Extracted {len(all_rules)} floor rules total")
    return all_rules
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/dungeons/test_extract_floor_rules.py -v
```
Expected: 8 PASSED

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/dungeons/extract_floor_rules.py tests/domains/dungeons/test_extract_floor_rules.py
git commit -m "feat: add extract_floor_rules extractor (portal, blizzard, deathswarm)"
```

---

### Task 9: extract_props.py — DCPropsDataAsset

**Files:**
- Create: `pipeline/domains/dungeons/extract_props.py`
- Create: `tests/domains/dungeons/test_extract_props.py`

- [ ] **Step 1: Write the failing tests**

`tests/domains/dungeons/test_extract_props.py`:
```python
"""Tests for pipeline/domains/dungeons/extract_props.py"""
import json
from pathlib import Path
from pipeline.domains.dungeons.extract_props import extract_prop, run_props


def make_prop_file(tmp_path, prop_id):
    data = [{
        "Type": "DCPropsDataAsset",
        "Name": prop_id,
        "Properties": {
            "IdTag": {"TagName": "Props.Barrel"},
            "Name": {"LocalizedString": "Barrel"},
            "GradeType": {"TagName": "Grade.Common"},
            "AdvPoint": 5,
            "ExpPoint": 10,
        }
    }]
    f = tmp_path / f"{prop_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_prop_returns_id_and_fields(tmp_path):
    f = make_prop_file(tmp_path, "Id_Props_Barrel")
    result = extract_prop(f)
    assert result is not None
    assert result["id"] == "Id_Props_Barrel"
    assert result["id_tag"] == "Props.Barrel"
    assert result["name"] == "Barrel"
    assert result["grade_type"] == "Grade.Common"
    assert result["adv_point"] == 5
    assert result["exp_point"] == 10


def test_extract_prop_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_prop(f) is None


def test_run_props_writes_entity_and_index(tmp_path):
    props_dir = tmp_path / "props"
    props_dir.mkdir()
    make_prop_file(props_dir, "Id_Props_Barrel")
    extracted = tmp_path / "extracted"
    result = run_props(props_dir=props_dir, extracted_root=extracted)
    entity = extracted / "dungeons" / "Id_Props_Barrel.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id_tag"] == "Props.Barrel"
    assert "_meta" in data
    assert "Id_Props_Barrel" in result
```

- [ ] **Step 2: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/dungeons/test_extract_props.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement pipeline/domains/dungeons/extract_props.py**

```python
"""Extract DCPropsDataAsset files → extracted/dungeons/<id>.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_tag, resolve_text
from pipeline.core.writer import Writer


def extract_prop(file_path: Path) -> dict | None:
    """Extract one DCPropsDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError):
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCPropsDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    return {
        "id": obj["Name"],
        "id_tag": resolve_tag(props.get("IdTag")),
        "name": resolve_text(props.get("Name")),
        "grade_type": resolve_tag(props.get("GradeType")),
        "adv_point": props.get("AdvPoint"),
        "exp_point": props.get("ExpPoint"),
    }


def run_props(props_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCPropsDataAsset files."""
    files = find_files(str(Path(props_dir) / "*.json"))
    print(f"  [props] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    props_map = {}

    for f in files:
        result = extract_prop(f)
        if not result:
            continue
        prop_id = result["id"]
        props_map[prop_id] = result
        writer.write_entity("dungeons", prop_id, result, source_files=[str(f)])
        index_entries.append({"id": prop_id})

    writer.write_index("dungeons", index_entries)
    print(f"  [props] Extracted {len(props_map)} props")
    return props_map
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/dungeons/test_extract_props.py -v
```
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/dungeons/extract_props.py tests/domains/dungeons/test_extract_props.py
git commit -m "feat: add extract_props extractor"
```

---

### Task 10: extract_props_effects.py — DCGameplayEffectDataAsset (Props/PropsEffect/)

**Files:**
- Create: `pipeline/domains/dungeons/extract_props_effects.py`
- Create: `tests/domains/dungeons/test_extract_props_effects.py`

NOTE: Same UE5 type as status domain but only `EffectClass`, `EventTag`, `AssetTags` present in `Props/PropsEffect/`. No `Duration` or `TargetType`.

- [ ] **Step 1: Write the failing tests**

`tests/domains/dungeons/test_extract_props_effects.py`:
```python
"""Tests for pipeline/domains/dungeons/extract_props_effects.py"""
import json
from pathlib import Path
from pipeline.domains.dungeons.extract_props_effects import extract_props_effect, run_props_effects


def make_props_effect_file(tmp_path, effect_id):
    data = [{
        "Type": "DCGameplayEffectDataAsset",
        "Name": effect_id,
        "Properties": {
            "EventTag": {"TagName": "Effect.Barrel.Explode"},
            "AssetTags": [
                {"TagName": "Tag.Destructible"},
                {"TagName": "Tag.Fire"},
            ],
        }
    }]
    f = tmp_path / f"{effect_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_props_effect_returns_id_and_fields(tmp_path):
    f = make_props_effect_file(tmp_path, "Id_PropsEffect_BarrelExplode")
    result = extract_props_effect(f)
    assert result is not None
    assert result["id"] == "Id_PropsEffect_BarrelExplode"
    assert result["event_tag"] == "Effect.Barrel.Explode"
    assert "Tag.Destructible" in result["asset_tags"]
    assert "Tag.Fire" in result["asset_tags"]


def test_extract_props_effect_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_props_effect(f) is None


def test_run_props_effects_writes_entity_and_index(tmp_path):
    effects_dir = tmp_path / "effects"
    effects_dir.mkdir()
    make_props_effect_file(effects_dir, "Id_PropsEffect_BarrelExplode")
    extracted = tmp_path / "extracted"
    result = run_props_effects(props_effect_dir=effects_dir, extracted_root=extracted)
    entity = extracted / "dungeons" / "Id_PropsEffect_BarrelExplode.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["event_tag"] == "Effect.Barrel.Explode"
    assert "_meta" in data
    assert "Id_PropsEffect_BarrelExplode" in result
```

- [ ] **Step 2: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/dungeons/test_extract_props_effects.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement pipeline/domains/dungeons/extract_props_effects.py**

```python
"""Extract DCGameplayEffectDataAsset (Props/PropsEffect/) → extracted/dungeons/<id>.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_tag
from pipeline.core.writer import Writer


def extract_props_effect(file_path: Path) -> dict | None:
    """Extract one DCGameplayEffectDataAsset file from Props/PropsEffect/.

    NOTE: Only EventTag and AssetTags are present in this sub-directory.
    Duration and TargetType (present in status domain) are absent here.
    """
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError):
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCGameplayEffectDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    return {
        "id": obj["Name"],
        "event_tag": resolve_tag(props.get("EventTag")),
        "asset_tags": [
            resolve_tag(t) for t in (props.get("AssetTags") or [])
            if resolve_tag(t) is not None
        ],
    }


def run_props_effects(props_effect_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCGameplayEffectDataAsset files from Props/PropsEffect/."""
    files = find_files(str(Path(props_effect_dir) / "*.json"))
    print(f"  [props_effects] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    effects = {}

    for f in files:
        result = extract_props_effect(f)
        if not result:
            continue
        effect_id = result["id"]
        effects[effect_id] = result
        writer.write_entity("dungeons", effect_id, result, source_files=[str(f)])
        index_entries.append({"id": effect_id})

    writer.write_index("dungeons", index_entries)
    print(f"  [props_effects] Extracted {len(effects)} props effects")
    return effects
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/dungeons/test_extract_props_effects.py -v
```
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/dungeons/extract_props_effects.py tests/domains/dungeons/test_extract_props_effects.py
git commit -m "feat: add extract_props_effects extractor"
```

---

### Task 11: extract_props_interacts.py — DCPropsInteractDataAsset

**Files:**
- Create: `pipeline/domains/dungeons/extract_props_interacts.py`
- Create: `tests/domains/dungeons/test_extract_props_interacts.py`

- [ ] **Step 1: Write the failing tests**

`tests/domains/dungeons/test_extract_props_interacts.py`:
```python
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
```

- [ ] **Step 2: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/dungeons/test_extract_props_interacts.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement pipeline/domains/dungeons/extract_props_interacts.py**

```python
"""Extract DCPropsInteractDataAsset files → extracted/dungeons/<id>.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_tag, resolve_text
from pipeline.core.writer import Writer


def extract_props_interact(file_path: Path) -> dict | None:
    """Extract one DCPropsInteractDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError):
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCPropsInteractDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    return {
        "id": obj["Name"],
        "interaction_name": resolve_text(props.get("InteractionName")),
        "interaction_text": resolve_text(props.get("InteractionText")),
        "duration": props.get("Duration"),
        "interactable_tag": resolve_tag(props.get("InteractableTag")),
        "trigger_tag": resolve_tag(props.get("TriggerTag")),
        "ability_trigger_tag": resolve_tag(props.get("AbilityTriggerTag")),
    }


def run_props_interacts(props_interact_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCPropsInteractDataAsset files."""
    files = find_files(str(Path(props_interact_dir) / "*.json"))
    print(f"  [props_interacts] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    interacts = {}

    for f in files:
        result = extract_props_interact(f)
        if not result:
            continue
        interact_id = result["id"]
        interacts[interact_id] = result
        writer.write_entity("dungeons", interact_id, result, source_files=[str(f)])
        index_entries.append({"id": interact_id})

    writer.write_index("dungeons", index_entries)
    print(f"  [props_interacts] Extracted {len(interacts)} props interacts")
    return interacts
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/dungeons/test_extract_props_interacts.py -v
```
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/dungeons/extract_props_interacts.py tests/domains/dungeons/test_extract_props_interacts.py
git commit -m "feat: add extract_props_interacts extractor"
```

---

### Task 12: extract_props_skill_checks.py — DCPropsSkillCheckDataAsset

**Files:**
- Create: `pipeline/domains/dungeons/extract_props_skill_checks.py`
- Create: `tests/domains/dungeons/test_extract_props_skill_checks.py`

- [ ] **Step 1: Write the failing tests**

`tests/domains/dungeons/test_extract_props_skill_checks.py`:
```python
"""Tests for pipeline/domains/dungeons/extract_props_skill_checks.py"""
import json
from pathlib import Path
from pipeline.domains.dungeons.extract_props_skill_checks import extract_props_skill_check, run_props_skill_checks


def make_skill_check_file(tmp_path, check_id):
    data = [{
        "Type": "DCPropsSkillCheckDataAsset",
        "Name": check_id,
        "Properties": {
            "SkillCheckType": "ESkillCheckType::Lockpick",
            "MinDuration": 1.0,
            "MaxDuration": 5.0,
            "MinSkillCheckInterval": 0.5,
            "MaxSkillCheckInterval": 2.0,
        }
    }]
    f = tmp_path / f"{check_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_props_skill_check_returns_id_and_fields(tmp_path):
    f = make_skill_check_file(tmp_path, "Id_PropsSkillCheck_Lockpick")
    result = extract_props_skill_check(f)
    assert result is not None
    assert result["id"] == "Id_PropsSkillCheck_Lockpick"
    assert result["skill_check_type"] == "ESkillCheckType::Lockpick"
    assert result["min_duration"] == 1.0
    assert result["max_duration"] == 5.0
    assert result["min_skill_check_interval"] == 0.5
    assert result["max_skill_check_interval"] == 2.0


def test_extract_props_skill_check_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_props_skill_check(f) is None


def test_run_props_skill_checks_writes_entity_and_index(tmp_path):
    checks_dir = tmp_path / "checks"
    checks_dir.mkdir()
    make_skill_check_file(checks_dir, "Id_PropsSkillCheck_Lockpick")
    extracted = tmp_path / "extracted"
    result = run_props_skill_checks(props_skill_check_dir=checks_dir, extracted_root=extracted)
    entity = extracted / "dungeons" / "Id_PropsSkillCheck_Lockpick.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["skill_check_type"] == "ESkillCheckType::Lockpick"
    assert "_meta" in data
    assert "Id_PropsSkillCheck_Lockpick" in result
```

- [ ] **Step 2: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/dungeons/test_extract_props_skill_checks.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement pipeline/domains/dungeons/extract_props_skill_checks.py**

```python
"""Extract DCPropsSkillCheckDataAsset files → extracted/dungeons/<id>.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.writer import Writer


def extract_props_skill_check(file_path: Path) -> dict | None:
    """Extract one DCPropsSkillCheckDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError):
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCPropsSkillCheckDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    return {
        "id": obj["Name"],
        "skill_check_type": props.get("SkillCheckType"),
        "min_duration": props.get("MinDuration"),
        "max_duration": props.get("MaxDuration"),
        "min_skill_check_interval": props.get("MinSkillCheckInterval"),
        "max_skill_check_interval": props.get("MaxSkillCheckInterval"),
    }


def run_props_skill_checks(props_skill_check_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCPropsSkillCheckDataAsset files."""
    files = find_files(str(Path(props_skill_check_dir) / "*.json"))
    print(f"  [props_skill_checks] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    checks = {}

    for f in files:
        result = extract_props_skill_check(f)
        if not result:
            continue
        check_id = result["id"]
        checks[check_id] = result
        writer.write_entity("dungeons", check_id, result, source_files=[str(f)])
        index_entries.append({"id": check_id})

    writer.write_index("dungeons", index_entries)
    print(f"  [props_skill_checks] Extracted {len(checks)} props skill checks")
    return checks
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/dungeons/test_extract_props_skill_checks.py -v
```
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/dungeons/extract_props_skill_checks.py tests/domains/dungeons/test_extract_props_skill_checks.py
git commit -m "feat: add extract_props_skill_checks extractor"
```

---

## Chunk 5: MapIcons + Vehicles + Orchestrator + Integration Test

### File Map

- Create: `pipeline/domains/dungeons/extract_map_icons.py`
- Create: `pipeline/domains/dungeons/extract_vehicles.py`
- Modify: `pipeline/domains/dungeons/__init__.py` (full orchestrator)
- Create: `tests/domains/dungeons/test_extract_map_icons.py`
- Create: `tests/domains/dungeons/test_extract_vehicles.py`
- Create: `tests/domains/dungeons/test_dungeons_integration.py`

---

### Task 13: extract_map_icons.py — DCMapIconDataAsset

**Files:**
- Create: `pipeline/domains/dungeons/extract_map_icons.py`
- Create: `tests/domains/dungeons/test_extract_map_icons.py`

NOTE: Source data has no `Properties` for map icons — only `id` is extracted.

- [ ] **Step 1: Write the failing tests**

`tests/domains/dungeons/test_extract_map_icons.py`:
```python
"""Tests for pipeline/domains/dungeons/extract_map_icons.py"""
import json
from pathlib import Path
from pipeline.domains.dungeons.extract_map_icons import extract_map_icon, run_map_icons


def make_map_icon_file(tmp_path, icon_id):
    data = [{"Type": "DCMapIconDataAsset", "Name": icon_id}]
    f = tmp_path / f"{icon_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_map_icon_returns_id(tmp_path):
    f = make_map_icon_file(tmp_path, "Id_MapIcon_Portal")
    result = extract_map_icon(f)
    assert result is not None
    assert result["id"] == "Id_MapIcon_Portal"


def test_extract_map_icon_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_map_icon(f) is None


def test_run_map_icons_writes_entity_and_index(tmp_path):
    icons_dir = tmp_path / "icons"
    icons_dir.mkdir()
    make_map_icon_file(icons_dir, "Id_MapIcon_Portal")
    extracted = tmp_path / "extracted"
    result = run_map_icons(map_icon_dir=icons_dir, extracted_root=extracted)
    entity = extracted / "dungeons" / "Id_MapIcon_Portal.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id"] == "Id_MapIcon_Portal"
    assert "_meta" in data
    assert "Id_MapIcon_Portal" in result
```

- [ ] **Step 2: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/dungeons/test_extract_map_icons.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement pipeline/domains/dungeons/extract_map_icons.py**

```python
"""Extract DCMapIconDataAsset files → extracted/dungeons/<id>.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files
from pipeline.core.writer import Writer


def extract_map_icon(file_path: Path) -> dict | None:
    """Extract one DCMapIconDataAsset file. Source data has no Properties."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError):
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCMapIconDataAsset"), None)
    if not obj:
        return None

    return {"id": obj["Name"]}


def run_map_icons(map_icon_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCMapIconDataAsset files."""
    files = find_files(str(Path(map_icon_dir) / "*.json"))
    print(f"  [map_icons] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    icons = {}

    for f in files:
        result = extract_map_icon(f)
        if not result:
            continue
        icon_id = result["id"]
        icons[icon_id] = result
        writer.write_entity("dungeons", icon_id, result, source_files=[str(f)])
        index_entries.append({"id": icon_id})

    writer.write_index("dungeons", index_entries)
    print(f"  [map_icons] Extracted {len(icons)} map icons")
    return icons
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/dungeons/test_extract_map_icons.py -v
```
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/dungeons/extract_map_icons.py tests/domains/dungeons/test_extract_map_icons.py
git commit -m "feat: add extract_map_icons extractor"
```

---

### Task 14: extract_vehicles.py — three asset types

**Files:**
- Create: `pipeline/domains/dungeons/extract_vehicles.py`
- Create: `tests/domains/dungeons/test_extract_vehicles.py`

NOTE: One file handles three types in `Vehicle/` sub-directory: `DCVehicleDataAsset`, `DCGameplayEffectDataAsset` (VehicleEffect/), `DCPropsInteractDataAsset` (VehicleInteract/). Skips `VehicleAbility/`.

- [ ] **Step 1: Write the failing tests**

`tests/domains/dungeons/test_extract_vehicles.py`:
```python
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
```

- [ ] **Step 2: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/dungeons/test_extract_vehicles.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement pipeline/domains/dungeons/extract_vehicles.py**

```python
"""Extract vehicle assets → extracted/dungeons/<id>.json.

Handles three types in Vehicle/ sub-directory:
  DCVehicleDataAsset          → Vehicle/Vehicle/
  DCGameplayEffectDataAsset   → Vehicle/VehicleEffect/
  DCPropsInteractDataAsset    → Vehicle/VehicleInteract/

Skips Vehicle/VehicleAbility/ (DCGameplayAbilityDataAsset).
"""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_tag, resolve_text
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


def extract_vehicle(file_path: Path) -> dict | None:
    """Extract one DCVehicleDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError):
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCVehicleDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    return {
        "id": obj["Name"],
        "id_tag": resolve_tag(props.get("IdTag")),
        "name": resolve_text(props.get("Name")),
        "swimming_movement_modifier": _extract_asset_id(props.get("SwimmingMovementModifier")),
    }


def extract_vehicle_effect(file_path: Path) -> dict | None:
    """Extract one DCGameplayEffectDataAsset file from Vehicle/VehicleEffect/."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError):
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCGameplayEffectDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    return {
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


def extract_vehicle_interact(file_path: Path) -> dict | None:
    """Extract one DCPropsInteractDataAsset file from Vehicle/VehicleInteract/."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError):
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCPropsInteractDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    return {
        "id": obj["Name"],
        "interaction_name": resolve_text(props.get("InteractionName")),
        "interaction_text": resolve_text(props.get("InteractionText")),
        "duration": props.get("Duration"),
        "interactable_tag": resolve_tag(props.get("InteractableTag")),
        "trigger_tag": resolve_tag(props.get("TriggerTag")),
        "ability_trigger_tag": resolve_tag(props.get("AbilityTriggerTag")),
    }


def run_vehicles(vehicle_dir: Path, extracted_root: Path) -> dict:
    """Extract all vehicle assets from sub-directories.

    Scans Vehicle/, VehicleEffect/, VehicleInteract/ under vehicle_dir.
    Skips VehicleAbility/ (DCGameplayAbilityDataAsset).
    Tags each entity with _entity_type. Returns combined {id: entity} dict.
    """
    vehicle_dir = Path(vehicle_dir)
    writer = Writer(extracted_root)
    all_vehicles = {}

    extractors = [
        ("Vehicle", extract_vehicle, "vehicle"),
        ("VehicleEffect", extract_vehicle_effect, "vehicle_effect"),
        ("VehicleInteract", extract_vehicle_interact, "vehicle_interact"),
    ]

    for subdir, extractor, entity_type in extractors:
        subdir_path = vehicle_dir / subdir
        if not subdir_path.exists():
            print(f"  [vehicles] WARNING: {subdir_path} not found")
            continue
        files = find_files(str(subdir_path / "*.json"))
        print(f"  [vehicles/{subdir}] Found {len(files)} files")
        for f in files:
            result = extractor(f)
            if not result:
                continue
            vid = result["id"]
            tagged = {**result, "_entity_type": entity_type}
            all_vehicles[vid] = tagged
            writer.write_entity("dungeons", vid, result, source_files=[str(f)])

    writer.write_index("dungeons", [{"id": v["id"]} for v in all_vehicles.values()])
    print(f"  [vehicles] Extracted {len(all_vehicles)} vehicle entities total")
    return all_vehicles
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/dungeons/test_extract_vehicles.py -v
```
Expected: 8 PASSED

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/dungeons/extract_vehicles.py tests/domains/dungeons/test_extract_vehicles.py
git commit -m "feat: add extract_vehicles extractor (vehicle, effect, interact)"
```

---

### Task 15: dungeons/__init__.py — orchestrator

**Files:**
- Modify: `pipeline/domains/dungeons/__init__.py`

- [ ] **Step 1: Replace the stub with the full orchestrator**

`pipeline/domains/dungeons/__init__.py`:
```python
"""Dungeons domain extractor — run() called by extract_all.py orchestrator."""
from pathlib import Path

from pipeline.domains.dungeons.extract_dungeons import run_dungeons
from pipeline.domains.dungeons.extract_dungeon_types import run_dungeon_types
from pipeline.domains.dungeons.extract_dungeon_grades import run_dungeon_grades
from pipeline.domains.dungeons.extract_dungeon_cards import run_dungeon_cards
from pipeline.domains.dungeons.extract_dungeon_layouts import run_dungeon_layouts
from pipeline.domains.dungeons.extract_dungeon_modules import run_dungeon_modules
from pipeline.domains.dungeons.extract_floor_rules import run_floor_rules
from pipeline.domains.dungeons.extract_props import run_props
from pipeline.domains.dungeons.extract_props_effects import run_props_effects
from pipeline.domains.dungeons.extract_props_interacts import run_props_interacts
from pipeline.domains.dungeons.extract_props_skill_checks import run_props_skill_checks
from pipeline.domains.dungeons.extract_map_icons import run_map_icons
from pipeline.domains.dungeons.extract_vehicles import run_vehicles
from pipeline.core.writer import Writer

_V2_BASE = "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2"


def run(raw_root: Path, extracted_root: Path) -> dict:
    """Run all dungeons domain extractors. Returns summary of counts."""
    print("[dungeons] Starting extraction...")
    summary = {}
    all_entities: dict[str, dict] = {}

    dirs = {
        "dungeon":           raw_root / _V2_BASE / "Dungeon" / "Dungeon",
        "dungeon_type":      raw_root / _V2_BASE / "Dungeon" / "DungeonType",
        "dungeon_grade":     raw_root / _V2_BASE / "Dungeon" / "DungeonGrade",
        "dungeon_card":      raw_root / _V2_BASE / "Dungeon" / "DungeonCard",
        "dungeon_layout":    raw_root / _V2_BASE / "Dungeon" / "DungeonLayout",
        "dungeon_module":    raw_root / _V2_BASE / "Dungeon" / "DungeonModule",
        "floor_rule":        raw_root / _V2_BASE / "FloorRule",
        "props":             raw_root / _V2_BASE / "Props" / "Props",
        "props_effect":      raw_root / _V2_BASE / "Props" / "PropsEffect",
        "props_interact":    raw_root / _V2_BASE / "Props" / "PropsInteract",
        "props_skill_check": raw_root / _V2_BASE / "Props" / "PropsSkillCheck",
        "map_icon":          raw_root / _V2_BASE / "MapIcon" / "MapIcon",
        "vehicle":           raw_root / _V2_BASE / "Vehicle",
    }

    # Run each single-directory extractor
    for key, fn, dir_key, entity_type, param in [
        ("dungeons",          run_dungeons,           "dungeon",           "dungeon",           "dungeon_dir"),
        ("dungeon_types",     run_dungeon_types,      "dungeon_type",      "dungeon_type",      "dungeon_type_dir"),
        ("dungeon_grades",    run_dungeon_grades,     "dungeon_grade",     "dungeon_grade",     "dungeon_grade_dir"),
        ("dungeon_cards",     run_dungeon_cards,      "dungeon_card",      "dungeon_card",      "dungeon_card_dir"),
        ("dungeon_layouts",   run_dungeon_layouts,    "dungeon_layout",    "dungeon_layout",    "dungeon_layout_dir"),
        ("dungeon_modules",   run_dungeon_modules,    "dungeon_module",    "dungeon_module",    "dungeon_module_dir"),
        ("props",             run_props,              "props",             "prop",              "props_dir"),
        ("props_effects",     run_props_effects,      "props_effect",      "props_effect",      "props_effect_dir"),
        ("props_interacts",   run_props_interacts,    "props_interact",    "props_interact",    "props_interact_dir"),
        ("props_skill_checks",run_props_skill_checks, "props_skill_check", "props_skill_check", "props_skill_check_dir"),
        ("map_icons",         run_map_icons,          "map_icon",          "map_icon",          "map_icon_dir"),
    ]:
        d = dirs[dir_key]
        if d.exists():
            entities = fn(**{param: d, "extracted_root": extracted_root})
            summary[key] = len(entities)
            all_entities.update({k: {**v, "_entity_type": entity_type}
                                  for k, v in entities.items()})
        else:
            print(f"  [dungeons] WARNING: {d} not found")
            summary[key] = 0

    # floor_rules and vehicles have custom directory structures
    floor_rule_dir = dirs["floor_rule"]
    if floor_rule_dir.exists():
        rules = run_floor_rules(floor_rule_dir=floor_rule_dir, extracted_root=extracted_root)
        summary["floor_rules"] = len(rules)
        all_entities.update({k: v for k, v in rules.items()})
    else:
        print(f"  [dungeons] WARNING: {floor_rule_dir} not found")
        summary["floor_rules"] = 0

    vehicle_dir = dirs["vehicle"]
    if vehicle_dir.exists():
        vehicles = run_vehicles(vehicle_dir=vehicle_dir, extracted_root=extracted_root)
        summary["vehicles"] = len(vehicles)
        all_entities.update({k: v for k, v in vehicles.items()})
    else:
        print(f"  [dungeons] WARNING: {vehicle_dir} not found")
        summary["vehicles"] = 0

    # Write combined index (overwrites partial indexes from individual run_* calls)
    combined_index = [
        {"id": v["id"], "type": v["_entity_type"]}
        for v in all_entities.values()
    ]
    Writer(extracted_root).write_index("dungeons", combined_index)

    print(f"[dungeons] Done. Summary: {summary}")
    return summary
```

- [ ] **Step 2: Run full dungeons test suite to verify nothing broke**

```bash
py -3 -m pytest tests/domains/dungeons/ -v --ignore=tests/domains/dungeons/test_dungeons_integration.py
```
Expected: All PASSED

- [ ] **Step 3: Commit**

```bash
git add pipeline/domains/dungeons/__init__.py
git commit -m "feat: complete dungeons orchestrator in __init__.py"
```

---

### Task 16: Integration test + full suite verification

**Files:**
- Create: `tests/domains/dungeons/test_dungeons_integration.py`

- [ ] **Step 1: Create the integration test**

`tests/domains/dungeons/test_dungeons_integration.py`:
```python
"""Integration test: run dungeons domain against real raw data."""
import json
from pathlib import Path
import pytest
from pipeline.domains.dungeons import run

RAW_ROOT = Path("raw")
DUNGEON_DIR = RAW_ROOT / "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/Dungeon/Dungeon"


@pytest.mark.skipif(not DUNGEON_DIR.exists(), reason="raw data not present")
def test_dungeons_run_integration(tmp_path):
    summary = run(raw_root=RAW_ROOT, extracted_root=tmp_path)
    assert summary.get("dungeons", 0) > 100
    assert summary.get("dungeon_types", 0) > 10
    assert summary.get("dungeon_grades", 0) > 50
    assert summary.get("dungeon_cards", 0) > 10
    assert summary.get("dungeon_layouts", 0) > 200
    assert summary.get("dungeon_modules", 0) > 200
    assert summary.get("floor_rules", 0) > 50
    assert summary.get("props", 0) > 800
    assert summary.get("props_effects", 0) > 100
    assert summary.get("props_interacts", 0) > 80
    assert summary.get("props_skill_checks", 0) > 0
    assert summary.get("map_icons", 0) > 10
    assert summary.get("vehicles", 0) > 0
    index = tmp_path / "dungeons" / "_index.json"
    assert index.exists()
    index_data = json.loads(index.read_text(encoding="utf-8"))
    entity_types = {e["type"] for e in index_data["entries"]}
    assert "dungeon" in entity_types
    assert "dungeon_type" in entity_types
    assert "dungeon_grade" in entity_types
    assert "prop" in entity_types
    assert "floor_portal" in entity_types
```

- [ ] **Step 2: Run full test suite to verify all tests pass**

```bash
py -3 -m pytest tests/ -v --tb=short 2>&1 | tail -20
```
Expected: All 136 prior tests + all new dungeons tests PASSED (integration test skipped if no raw data)

- [ ] **Step 3: Commit**

```bash
git add tests/domains/dungeons/test_dungeons_integration.py
git commit -m "test: add dungeons integration test"
```
