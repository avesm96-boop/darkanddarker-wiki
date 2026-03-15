# Phase 6a: Quests Domain Extractor Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `pipeline/domains/quests/` with 5 sub-extractors producing `extracted/quests/<id>.json` entity files and a combined `_index.json`.

**Architecture:** Each sub-extractor is a focused module with one `extract_*()` function and one `run_*()` function. `__init__.py` orchestrates all five sub-extractors and writes a single combined index, following the exact pattern of `pipeline/domains/spawns/__init__.py`. `extract_quests.py`, `extract_achievements.py`, and `extract_leaderboards.py` each define a local `_extract_asset_id()` helper (same pattern as `extract_spawners.py`). `extract_triumph_levels.py` and `extract_announces.py` do not need `_extract_asset_id`.

**Tech Stack:** Python 3.10+, pytest, pathlib, pipeline.core (reader, writer, normalizer)

**Spec:** `docs/superpowers/specs/2026-03-12-full-extraction-pipeline-design.md` §3, §5, §6

---

## Chunk 1: Test Infrastructure + Tasks 2-4 (quests, achievements, triumph_levels)

### File Map

- Create: `pipeline/domains/quests/__init__.py` (stub then full orchestrator)
- Create: `pipeline/domains/quests/extract_quests.py`
- Create: `pipeline/domains/quests/extract_achievements.py`
- Create: `pipeline/domains/quests/extract_triumph_levels.py`
- Create: `tests/domains/quests/__init__.py`
- Create: `tests/domains/quests/test_extract_quests.py`
- Create: `tests/domains/quests/test_extract_achievements.py`
- Create: `tests/domains/quests/test_extract_triumph_levels.py`

---

### Task 1: Test infrastructure

**Files:**
- Create: `pipeline/domains/quests/__init__.py` (empty stub)
- Create: `tests/domains/quests/__init__.py` (empty)

- [ ] **Step 1: Create the two empty `__init__.py` files**

`pipeline/domains/quests/__init__.py`:
```python
"""Quests domain extractor — run() called by extract_all.py orchestrator."""
```

`tests/domains/quests/__init__.py`:
```python
```
(empty file)

- [ ] **Step 2: Verify pytest can collect from the new directory**

Run from `darkanddarker-wiki/`:
```bash
py -3 -m pytest tests/domains/quests/ --collect-only
```
Expected: `no tests ran`

---

### Task 2: extract_quests.py — DCQuestDataAsset

**Files:**
- Create: `pipeline/domains/quests/extract_quests.py`
- Create: `tests/domains/quests/test_extract_quests.py`

- [ ] **Step 1: Write the failing tests**

`tests/domains/quests/test_extract_quests.py`:
```python
"""Tests for pipeline/domains/quests/extract_quests.py"""
import json
from pathlib import Path
from pipeline.domains.quests.extract_quests import extract_quest, run_quests


def make_quest_file(tmp_path, quest_id, required_quest=None, required_level=None):
    props = {}
    if required_quest:
        props["RequiredQuest"] = {
            "AssetPathName": f"/Game/.../Quest/{required_quest}.{required_quest}",
            "SubPathString": "",
        }
    if required_level is not None:
        props["RequiredLevel"] = required_level
    data = [{"Type": "DCQuestDataAsset", "Name": quest_id, "Properties": props}]
    f = tmp_path / f"{quest_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_quest_returns_id_and_fields(tmp_path):
    f = make_quest_file(
        tmp_path,
        "Id_Quest_Alchemist_01",
        required_quest="Id_Quest_Treasurer_06",
        required_level=114,
    )
    result = extract_quest(f)
    assert result is not None
    assert result["id"] == "Id_Quest_Alchemist_01"
    assert result["required_quest"] == "Id_Quest_Treasurer_06"
    assert result["required_level"] == 114


def test_extract_quest_handles_missing_optional_fields(tmp_path):
    f = make_quest_file(tmp_path, "Id_Quest_Simple_01")
    result = extract_quest(f)
    assert result is not None
    assert result["id"] == "Id_Quest_Simple_01"
    assert result["required_quest"] is None
    assert result["required_level"] is None


def test_extract_quest_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_quest(f) is None


def test_run_quests_writes_entity_and_index(tmp_path):
    quest_dir = tmp_path / "quests"
    quest_dir.mkdir()
    make_quest_file(
        quest_dir,
        "Id_Quest_Alchemist_01",
        required_quest="Id_Quest_Treasurer_06",
        required_level=114,
    )
    extracted = tmp_path / "extracted"
    result = run_quests(quest_dir=quest_dir, extracted_root=extracted)
    entity = extracted / "quests" / "Id_Quest_Alchemist_01.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id"] == "Id_Quest_Alchemist_01"
    assert data["required_quest"] == "Id_Quest_Treasurer_06"
    assert data["required_level"] == 114
    assert "_meta" in data
    index = extracted / "quests" / "_index.json"
    assert index.exists()
    assert "Id_Quest_Alchemist_01" in result
```

- [ ] **Step 2: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/quests/test_extract_quests.py -v
```
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement pipeline/domains/quests/extract_quests.py**

```python
"""Extract DCQuestDataAsset files → extracted/quests/<id>.json + _index.json."""
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


def extract_quest(file_path: Path) -> dict | None:
    """Extract one DCQuestDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCQuestDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)

    return {
        "id": obj["Name"],
        "required_quest": _extract_asset_id(props.get("RequiredQuest")),
        "required_level": props.get("RequiredLevel"),
    }


def run_quests(quest_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCQuestDataAsset files."""
    files = find_files(str(Path(quest_dir) / "*.json"))
    print(f"  [quests] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    quests = {}

    for f in files:
        result = extract_quest(f)
        if not result:
            continue
        quest_id = result["id"]
        quests[quest_id] = result
        writer.write_entity("quests", quest_id, result, source_files=[str(f)])
        index_entries.append({"id": quest_id})

    writer.write_index("quests", index_entries)
    print(f"  [quests] Extracted {len(quests)} quests")
    return quests
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/quests/test_extract_quests.py -v
```
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/quests/__init__.py pipeline/domains/quests/extract_quests.py tests/domains/quests/__init__.py tests/domains/quests/test_extract_quests.py
git commit -m "feat: add quests domain + extract_quests extractor"
```

---

### Task 3: extract_achievements.py — DCAchievementDataAsset

**Files:**
- Create: `pipeline/domains/quests/extract_achievements.py`
- Create: `tests/domains/quests/test_extract_achievements.py`

- [ ] **Step 1: Write the failing tests**

`tests/domains/quests/test_extract_achievements.py`:
```python
"""Tests for pipeline/domains/quests/extract_achievements.py"""
import json
from pathlib import Path
from pipeline.domains.quests.extract_achievements import extract_achievement, run_achievements


def make_achievement_file(tmp_path, achievement_id):
    data = [{
        "Type": "DCAchievementDataAsset",
        "Name": achievement_id,
        "Properties": {
            "Enable": True,
            "ListingOrder": 139,
            "MainCategory": "EDCAchievementMainCategory::Arena",
            "MainCategoryText": {"Namespace": "DC", "LocalizedString": "Arena"},
            "Name": {"Namespace": "DC", "LocalizedString": "First Blood"},
            "Description": {"Namespace": "DC", "LocalizedString": "Win an Arena match for the first time."},
            "ObjectiveId": [
                {
                    "AssetPathName": "/Game/.../Objective_GameResult_12.Objective_GameResult_12",
                    "SubPathString": "",
                }
            ],
            "SequenceGroupOrder": 1,
            "SequenceGroup": "EDCAchievementSequenceGroup::Achievement_Group_Arena_Win",
            "ArtData": {
                "AssetPathName": "/Game/.../WinningArena.WinningArena",
                "SubPathString": "",
            },
        },
    }]
    f = tmp_path / f"{achievement_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_achievement_returns_id_and_fields(tmp_path):
    f = make_achievement_file(tmp_path, "Achievement_Arena_01")
    result = extract_achievement(f)
    assert result is not None
    assert result["id"] == "Achievement_Arena_01"
    assert result["enabled"] is True
    assert result["listing_order"] == 139
    assert result["main_category"] == "Arena"
    assert result["main_category_text"] == "Arena"
    assert result["name"] == "First Blood"
    assert result["description"] == "Win an Arena match for the first time."
    assert result["objective_ids"] == ["Objective_GameResult_12"]
    assert result["sequence_group_order"] == 1
    assert result["sequence_group"] == "Achievement_Group_Arena_Win"
    assert result["art_data"] == "WinningArena"


def test_extract_achievement_handles_empty_objective_ids(tmp_path):
    data = [{
        "Type": "DCAchievementDataAsset",
        "Name": "Achievement_Empty_01",
        "Properties": {
            "Enable": False,
            "ObjectiveId": [],
        },
    }]
    f = tmp_path / "empty.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    result = extract_achievement(f)
    assert result is not None
    assert result["objective_ids"] == []


def test_extract_achievement_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_achievement(f) is None


def test_run_achievements_writes_entity_and_index(tmp_path):
    achievement_dir = tmp_path / "achievements"
    achievement_dir.mkdir()
    make_achievement_file(achievement_dir, "Achievement_Arena_01")
    extracted = tmp_path / "extracted"
    result = run_achievements(achievement_dir=achievement_dir, extracted_root=extracted)
    entity = extracted / "quests" / "Achievement_Arena_01.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id"] == "Achievement_Arena_01"
    assert data["name"] == "First Blood"
    assert data["objective_ids"] == ["Objective_GameResult_12"]
    assert "_meta" in data
    index = extracted / "quests" / "_index.json"
    assert index.exists()
    assert "Achievement_Arena_01" in result
```

- [ ] **Step 2: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/quests/test_extract_achievements.py -v
```
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement pipeline/domains/quests/extract_achievements.py**

```python
"""Extract DCAchievementDataAsset files → extracted/quests/<id>.json + _index.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_text
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


def extract_achievement(file_path: Path) -> dict | None:
    """Extract one DCAchievementDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCAchievementDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)

    return {
        "id": obj["Name"],
        "enabled": props.get("Enable", False),
        "listing_order": props.get("ListingOrder"),
        "main_category": (lambda v: v.split("::")[-1] if v and "::" in v else v)(props.get("MainCategory")),
        "main_category_text": resolve_text(props.get("MainCategoryText")),
        "name": resolve_text(props.get("Name")),
        "description": resolve_text(props.get("Description")),
        "objective_ids": [
            _extract_asset_id(ref)
            for ref in (props.get("ObjectiveId") or [])
        ],
        "sequence_group_order": props.get("SequenceGroupOrder"),
        "sequence_group": (lambda v: v.split("::")[-1] if v and "::" in v else v)(props.get("SequenceGroup")),
        "art_data": _extract_asset_id(props.get("ArtData")),
    }


def run_achievements(achievement_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCAchievementDataAsset files."""
    files = find_files(str(Path(achievement_dir) / "*.json"))
    print(f"  [achievements] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    achievements = {}

    for f in files:
        result = extract_achievement(f)
        if not result:
            continue
        achievement_id = result["id"]
        achievements[achievement_id] = result
        writer.write_entity("quests", achievement_id, result, source_files=[str(f)])
        index_entries.append({"id": achievement_id})

    writer.write_index("quests", index_entries)
    print(f"  [achievements] Extracted {len(achievements)} achievements")
    return achievements
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/quests/test_extract_achievements.py -v
```
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/quests/extract_achievements.py tests/domains/quests/test_extract_achievements.py
git commit -m "feat: add extract_achievements extractor"
```

---

### Task 4: extract_triumph_levels.py — DCTriumphLevelDataAsset

**Files:**
- Create: `pipeline/domains/quests/extract_triumph_levels.py`
- Create: `tests/domains/quests/test_extract_triumph_levels.py`

- [ ] **Step 1: Write the failing tests**

`tests/domains/quests/test_extract_triumph_levels.py`:
```python
"""Tests for pipeline/domains/quests/extract_triumph_levels.py"""
import json
from pathlib import Path
from pipeline.domains.quests.extract_triumph_levels import extract_triumph_level, run_triumph_levels


def make_triumph_level_file(tmp_path, triumph_level_id):
    data = [{"Type": "DCTriumphLevelDataAsset", "Name": triumph_level_id}]
    f = tmp_path / f"{triumph_level_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_triumph_level_returns_id_and_fields(tmp_path):
    f = make_triumph_level_file(tmp_path, "Id_TriumphLevel_0")
    result = extract_triumph_level(f)
    assert result is not None
    assert result["id"] == "Id_TriumphLevel_0"


def test_extract_triumph_level_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_triumph_level(f) is None


def test_run_triumph_levels_writes_entity_and_index(tmp_path):
    triumph_level_dir = tmp_path / "triumph_levels"
    triumph_level_dir.mkdir()
    make_triumph_level_file(triumph_level_dir, "Id_TriumphLevel_0")
    make_triumph_level_file(triumph_level_dir, "Id_TriumphLevel_1")
    extracted = tmp_path / "extracted"
    result = run_triumph_levels(triumph_level_dir=triumph_level_dir, extracted_root=extracted)
    entity = extracted / "quests" / "Id_TriumphLevel_0.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id"] == "Id_TriumphLevel_0"
    assert "_meta" in data
    index = extracted / "quests" / "_index.json"
    assert index.exists()
    assert "Id_TriumphLevel_0" in result
    assert "Id_TriumphLevel_1" in result
```

- [ ] **Step 2: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/quests/test_extract_triumph_levels.py -v
```
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement pipeline/domains/quests/extract_triumph_levels.py**

```python
"""Extract DCTriumphLevelDataAsset files → extracted/quests/<id>.json + _index.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files
from pipeline.core.writer import Writer


def extract_triumph_level(file_path: Path) -> dict | None:
    """Extract one DCTriumphLevelDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCTriumphLevelDataAsset"), None)
    if not obj:
        return None

    return {
        "id": obj["Name"],
    }


def run_triumph_levels(triumph_level_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCTriumphLevelDataAsset files."""
    files = find_files(str(Path(triumph_level_dir) / "*.json"))
    print(f"  [triumph_levels] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    triumph_levels = {}

    for f in files:
        result = extract_triumph_level(f)
        if not result:
            continue
        triumph_level_id = result["id"]
        triumph_levels[triumph_level_id] = result
        writer.write_entity("quests", triumph_level_id, result, source_files=[str(f)])
        index_entries.append({"id": triumph_level_id})

    writer.write_index("quests", index_entries)
    print(f"  [triumph_levels] Extracted {len(triumph_levels)} triumph levels")
    return triumph_levels
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/quests/test_extract_triumph_levels.py -v
```
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/quests/extract_triumph_levels.py tests/domains/quests/test_extract_triumph_levels.py
git commit -m "feat: add extract_triumph_levels extractor"
```

---

## Chunk 2: Tasks 5-8 (leaderboards, announces, orchestrator, integration test)

### File Map

- Create: `pipeline/domains/quests/extract_leaderboards.py`
- Create: `pipeline/domains/quests/extract_announces.py`
- Modify: `pipeline/domains/quests/__init__.py` (full orchestrator)
- Create: `tests/domains/quests/test_extract_leaderboards.py`
- Create: `tests/domains/quests/test_extract_announces.py`
- Create: `tests/domains/quests/test_quests_integration.py`

---

### Task 5: extract_leaderboards.py — DCLeaderboardDataAsset

**Files:**
- Create: `pipeline/domains/quests/extract_leaderboards.py`
- Create: `tests/domains/quests/test_extract_leaderboards.py`

- [ ] **Step 1: Write the failing tests**

`tests/domains/quests/test_extract_leaderboards.py`:
```python
"""Tests for pipeline/domains/quests/extract_leaderboards.py"""
import json
from pathlib import Path
from pipeline.domains.quests.extract_leaderboards import extract_leaderboard, run_leaderboards


def make_leaderboard_file(tmp_path, leaderboard_id):
    data = [{
        "Type": "DCLeaderboardDataAsset",
        "Name": leaderboard_id,
        "Properties": {
            "SeasonName": {"Namespace": "DC", "LocalizedString": "Arena Test 1"},
            "LeaderboardType": "EDCLeaderboardType::Arena",
            "LeaderboardSheets": [
                {
                    "AssetPathName": "/Game/.../Id_LeaderboardSheet_ArenaTrio.Id_LeaderboardSheet_ArenaTrio",
                    "SubPathString": "",
                }
            ],
            "LeaderboardRanks": [
                {
                    "AssetPathName": "/Game/.../Id_LeaderboardRank_Cadet.Id_LeaderboardRank_Cadet",
                    "SubPathString": "",
                },
                {
                    "AssetPathName": "/Game/.../Id_LeaderboardRank_Squire.Id_LeaderboardRank_Squire",
                    "SubPathString": "",
                },
            ],
            "Order": 5,
        },
    }]
    f = tmp_path / f"{leaderboard_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_leaderboard_returns_id_and_fields(tmp_path):
    f = make_leaderboard_file(tmp_path, "Id_Leaderboard_Arena_Preseason")
    result = extract_leaderboard(f)
    assert result is not None
    assert result["id"] == "Id_Leaderboard_Arena_Preseason"
    assert result["season_name"] == "Arena Test 1"
    assert result["leaderboard_type"] == "Arena"
    assert result["leaderboard_sheets"] == ["Id_LeaderboardSheet_ArenaTrio"]
    assert result["leaderboard_ranks"] == [
        "Id_LeaderboardRank_Cadet",
        "Id_LeaderboardRank_Squire",
    ]
    assert result["order"] == 5


def test_extract_leaderboard_handles_empty_arrays(tmp_path):
    data = [{
        "Type": "DCLeaderboardDataAsset",
        "Name": "Id_Leaderboard_Empty",
        "Properties": {
            "LeaderboardSheets": [],
            "LeaderboardRanks": [],
        },
    }]
    f = tmp_path / "empty.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    result = extract_leaderboard(f)
    assert result is not None
    assert result["leaderboard_sheets"] == []
    assert result["leaderboard_ranks"] == []


def test_extract_leaderboard_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_leaderboard(f) is None


def test_run_leaderboards_writes_entity_and_index(tmp_path):
    leaderboard_dir = tmp_path / "leaderboards"
    leaderboard_dir.mkdir()
    make_leaderboard_file(leaderboard_dir, "Id_Leaderboard_Arena_Preseason")
    extracted = tmp_path / "extracted"
    result = run_leaderboards(leaderboard_dir=leaderboard_dir, extracted_root=extracted)
    entity = extracted / "quests" / "Id_Leaderboard_Arena_Preseason.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id"] == "Id_Leaderboard_Arena_Preseason"
    assert data["season_name"] == "Arena Test 1"
    assert len(data["leaderboard_ranks"]) == 2
    assert "_meta" in data
    index = extracted / "quests" / "_index.json"
    assert index.exists()
    assert "Id_Leaderboard_Arena_Preseason" in result
```

- [ ] **Step 2: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/quests/test_extract_leaderboards.py -v
```
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement pipeline/domains/quests/extract_leaderboards.py**

```python
"""Extract DCLeaderboardDataAsset files → extracted/quests/<id>.json + _index.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_text
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


def extract_leaderboard(file_path: Path) -> dict | None:
    """Extract one DCLeaderboardDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCLeaderboardDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)

    return {
        "id": obj["Name"],
        "season_name": resolve_text(props.get("SeasonName")),
        "leaderboard_type": (lambda v: v.split("::")[-1] if v and "::" in v else v)(props.get("LeaderboardType")),
        "leaderboard_sheets": [
            _extract_asset_id(ref)
            for ref in (props.get("LeaderboardSheets") or [])
        ],
        "leaderboard_ranks": [
            _extract_asset_id(ref)
            for ref in (props.get("LeaderboardRanks") or [])
        ],
        "order": props.get("Order"),
    }


def run_leaderboards(leaderboard_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCLeaderboardDataAsset files."""
    files = find_files(str(Path(leaderboard_dir) / "*.json"))
    print(f"  [leaderboards] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    leaderboards = {}

    for f in files:
        result = extract_leaderboard(f)
        if not result:
            continue
        leaderboard_id = result["id"]
        leaderboards[leaderboard_id] = result
        writer.write_entity("quests", leaderboard_id, result, source_files=[str(f)])
        index_entries.append({"id": leaderboard_id})

    writer.write_index("quests", index_entries)
    print(f"  [leaderboards] Extracted {len(leaderboards)} leaderboards")
    return leaderboards
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/quests/test_extract_leaderboards.py -v
```
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/quests/extract_leaderboards.py tests/domains/quests/test_extract_leaderboards.py
git commit -m "feat: add extract_leaderboards extractor"
```

---

### Task 6: extract_announces.py — DCAnnounceDataAsset

**Files:**
- Create: `pipeline/domains/quests/extract_announces.py`
- Create: `tests/domains/quests/test_extract_announces.py`

- [ ] **Step 1: Write the failing tests**

`tests/domains/quests/test_extract_announces.py`:
```python
"""Tests for pipeline/domains/quests/extract_announces.py"""
import json
from pathlib import Path
from pipeline.domains.quests.extract_announces import extract_announce, run_announces


def make_announce_file(tmp_path, announce_id, text="The server will be down for maintenance in {0} minutes."):
    data = [{
        "Type": "DCAnnounceDataAsset",
        "Name": announce_id,
        "Properties": {
            "AnnounceText": {"Namespace": "DC", "LocalizedString": text},
        },
    }]
    f = tmp_path / f"{announce_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_announce_returns_id_and_fields(tmp_path):
    f = make_announce_file(tmp_path, "Id_Announce_AllMaintenaceAnnounce")
    result = extract_announce(f)
    assert result is not None
    assert result["id"] == "Id_Announce_AllMaintenaceAnnounce"
    assert result["announce_text"] == "The server will be down for maintenance in {0} minutes."


def test_extract_announce_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_announce(f) is None


def test_run_announces_writes_entity_and_index(tmp_path):
    announce_dir = tmp_path / "announces"
    announce_dir.mkdir()
    make_announce_file(announce_dir, "Id_Announce_AllMaintenaceAnnounce")
    make_announce_file(announce_dir, "Id_Announce_UpdateAnnounce", text="New patch available.")
    extracted = tmp_path / "extracted"
    result = run_announces(announce_dir=announce_dir, extracted_root=extracted)
    entity = extracted / "quests" / "Id_Announce_AllMaintenaceAnnounce.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id"] == "Id_Announce_AllMaintenaceAnnounce"
    assert "maintenance" in data["announce_text"]
    assert "_meta" in data
    index = extracted / "quests" / "_index.json"
    assert index.exists()
    assert "Id_Announce_AllMaintenaceAnnounce" in result
    assert "Id_Announce_UpdateAnnounce" in result
```

- [ ] **Step 2: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/quests/test_extract_announces.py -v
```
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement pipeline/domains/quests/extract_announces.py**

```python
"""Extract DCAnnounceDataAsset files → extracted/quests/<id>.json + _index.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_text
from pipeline.core.writer import Writer


def extract_announce(file_path: Path) -> dict | None:
    """Extract one DCAnnounceDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCAnnounceDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)

    return {
        "id": obj["Name"],
        "announce_text": resolve_text(props.get("AnnounceText")),
    }


def run_announces(announce_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCAnnounceDataAsset files."""
    files = find_files(str(Path(announce_dir) / "*.json"))
    print(f"  [announces] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    announces = {}

    for f in files:
        result = extract_announce(f)
        if not result:
            continue
        announce_id = result["id"]
        announces[announce_id] = result
        writer.write_entity("quests", announce_id, result, source_files=[str(f)])
        index_entries.append({"id": announce_id})

    writer.write_index("quests", index_entries)
    print(f"  [announces] Extracted {len(announces)} announces")
    return announces
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/quests/test_extract_announces.py -v
```
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/quests/extract_announces.py tests/domains/quests/test_extract_announces.py
git commit -m "feat: add extract_announces extractor"
```

---

### Task 7: quests/__init__.py — orchestrator

**Files:**
- Modify: `pipeline/domains/quests/__init__.py`

- [ ] **Step 1: Replace the stub with the full orchestrator**

`pipeline/domains/quests/__init__.py`:
```python
"""Quests domain extractor — run() called by extract_all.py orchestrator."""
from pathlib import Path

from pipeline.domains.quests.extract_quests import run_quests
from pipeline.domains.quests.extract_achievements import run_achievements
from pipeline.domains.quests.extract_triumph_levels import run_triumph_levels
from pipeline.domains.quests.extract_leaderboards import run_leaderboards
from pipeline.domains.quests.extract_announces import run_announces
from pipeline.core.writer import Writer

_V2_BASE = "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2"


def run(raw_root: Path, extracted_root: Path) -> dict:
    """Run all quests domain extractors. Returns summary of counts.

    NOTE: Individual run_* functions each write a partial _index.json as a
    side-effect (useful for standalone runs / unit tests). This orchestrator
    overwrites that partial index with a single combined index containing all
    entity types at the end.
    """
    print("[quests] Starting extraction...")
    summary = {}
    all_entities: dict[str, dict] = {}

    dirs = {
        "quest":         raw_root / _V2_BASE / "Quest" / "Quest",
        "achievement":   raw_root / _V2_BASE / "Achievement" / "Achievement",
        "triumph_level": raw_root / _V2_BASE / "TriumphLevel" / "TriumphLevel",
        "leaderboard":   raw_root / _V2_BASE / "Leaderboard" / "Leaderboard",
        "announce":      raw_root / _V2_BASE / "Announce" / "Announce",
    }

    for key, fn, dir_key, entity_type, param in [
        ("quests",         run_quests,         "quest",         "quest",         "quest_dir"),
        ("achievements",   run_achievements,   "achievement",   "achievement",   "achievement_dir"),
        ("triumph_levels", run_triumph_levels, "triumph_level", "triumph_level", "triumph_level_dir"),
        ("leaderboards",   run_leaderboards,   "leaderboard",   "leaderboard",   "leaderboard_dir"),
        ("announces",      run_announces,      "announce",      "announce",      "announce_dir"),
    ]:
        d = dirs[dir_key]
        if d.exists():
            entities = fn(**{param: d, "extracted_root": extracted_root})
            summary[key] = len(entities)
            all_entities.update({k: {**v, "_entity_type": entity_type}
                                  for k, v in entities.items()})
        else:
            print(f"  [quests] WARNING: {d} not found")
            summary[key] = 0

    # Write combined index (overwrites partial indexes from individual run_* calls)
    combined_index = [
        {"id": v["id"], "type": v["_entity_type"]}
        for v in all_entities.values()
    ]
    Writer(extracted_root).write_index("quests", combined_index)

    print(f"[quests] Done. Summary: {summary}")
    return summary
```

- [ ] **Step 2: Run full quests test suite to verify nothing broke**

```bash
py -3 -m pytest tests/domains/quests/ -v --ignore=tests/domains/quests/test_quests_integration.py
```
Expected: All PASSED

- [ ] **Step 3: Commit**

```bash
git add pipeline/domains/quests/__init__.py
git commit -m "feat: complete quests orchestrator in __init__.py"
```

---

### Task 8: Integration test + full suite verification

**Files:**
- Create: `tests/domains/quests/test_quests_integration.py`

- [ ] **Step 1: Create the integration test**

`tests/domains/quests/test_quests_integration.py`:
```python
"""Integration test: run quests domain against real raw data."""
import json
from pathlib import Path
import pytest
from pipeline.domains.quests import run

RAW_ROOT = Path("raw")
QUEST_DIR = RAW_ROOT / "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/Quest/Quest"


@pytest.mark.skipif(not QUEST_DIR.exists(), reason="raw data not present")
def test_quests_run_integration(tmp_path):
    summary = run(raw_root=RAW_ROOT, extracted_root=tmp_path)
    assert summary.get("quests", 0) > 1000
    assert summary.get("achievements", 0) > 500
    assert summary.get("triumph_levels", 0) >= 10
    assert summary.get("leaderboards", 0) > 100
    assert summary.get("announces", 0) >= 2
    index = tmp_path / "quests" / "_index.json"
    assert index.exists()
    index_data = json.loads(index.read_text(encoding="utf-8"))
    entity_types = {e["type"] for e in index_data["entries"]}
    assert "quest" in entity_types
    assert "achievement" in entity_types
    assert "triumph_level" in entity_types
    assert "leaderboard" in entity_types
    assert "announce" in entity_types
```

- [ ] **Step 2: Run full test suite to verify all tests pass**

```bash
py -3 -m pytest tests/ -v --tb=short 2>&1 | tail -20
```
Expected: All prior tests + all new quests tests PASSED (integration test skipped if no raw data)

- [ ] **Step 3: Commit**

```bash
git add tests/domains/quests/test_quests_integration.py
git commit -m "test: add quests integration test"
```

---

## Final verification

- [ ] **Run the complete test suite one final time**

```bash
py -3 -m pytest tests/ --tb=short 2>&1 | tail -5
```
Expected: All tests passed, 0 failures
