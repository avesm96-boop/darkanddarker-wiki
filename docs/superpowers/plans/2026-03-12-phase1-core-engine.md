# Phase 1: Core Library + Engine Domain Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `pipeline/core/` shared library and `pipeline/domains/engine/` domain extractor, producing `extracted/engine/enums.json`, `extracted/engine/constants.json`, `extracted/engine/curves.json`, and `extracted/engine/tags.json`.

**Architecture:** A shared `core/` library with 5 modules (reader, normalizer, resolver, writer, analyzer) is built test-first. The `engine` domain package then uses `core/` to extract all engine-level game data. Old pipeline stubs are deleted and `utils.py` becomes a thin re-export shim.

**Tech Stack:** Python 3.10+, pytest, pathlib, json, concurrent.futures (resolver thread safety), datetime/timezone

---

## Chunk 1: Dev Environment + Core Reader

### File Map

- Create: `requirements-dev.txt`
- Create: `tests/__init__.py`
- Create: `tests/fixtures/` (directory for test JSON files)
- Create: `tests/core/__init__.py`
- Create: `tests/core/test_reader.py`
- Create: `pipeline/core/__init__.py`
- Create: `pipeline/core/reader.py`

---

### Task 1: Dev dependencies

**Files:**
- Create: `requirements-dev.txt`

- [ ] **Step 1: Create requirements-dev.txt**

```
pytest>=7.0
pytest-mock>=3.0
```

- [ ] **Step 2: Install dev dependencies**

Run from `darkanddarker-wiki/` directory:
```bash
py -3 -m pip install -r requirements-dev.txt
```
Expected: `Successfully installed pytest-...`

- [ ] **Step 3: Verify pytest works**

```bash
py -3 -m pytest --version
```
Expected: `pytest 7.x.x`

- [ ] **Step 4: Commit**

```bash
git add requirements-dev.txt
git commit -m "chore: add pytest dev dependencies"
```

---

### Task 2: Test fixtures

**Files:**
- Create: `tests/__init__.py` (empty)
- Create: `tests/core/__init__.py` (empty)
- Create: `tests/fixtures/sample_enum.json`
- Create: `tests/fixtures/sample_v2_item.json`
- Create: `tests/fixtures/sample_v2_multi.json`

- [ ] **Step 1: Create test directory structure**

Run from the `darkanddarker-wiki/` directory for all commands in this plan.

```bash
py -3 -c "
from pathlib import Path
for d in ['tests/core', 'tests/fixtures']:
    Path(d).mkdir(parents=True, exist_ok=True)
for f in ['tests/__init__.py', 'tests/core/__init__.py']:
    Path(f).touch()
print('done')
"
```

- [ ] **Step 2: Create sample_enum.json fixture**

`tests/fixtures/sample_enum.json`:
```json
[
  {
    "Type": "UserDefinedEnum",
    "Name": "E_TestEnum",
    "Names": {
      "E_TestEnum::NewEnumerator0": 0,
      "E_TestEnum::NewEnumerator1": 1,
      "E_TestEnum::_MAX": 2
    },
    "Properties": {}
  }
]
```

- [ ] **Step 3: Create sample_v2_item.json fixture** (single V2 object with Properties.Item)

`tests/fixtures/sample_v2_item.json`:
```json
[
  {
    "Type": "DCItemDataAsset",
    "Name": "Id_Item_Longsword",
    "Properties": {
      "Item": {
        "ItemId": {
          "ObjectName": "Id_Item_Longsword",
          "ObjectPath": "/Game/Data/Item/Id_Item_Longsword.0"
        },
        "ItemName": { "LocalizedString": "Longsword" },
        "MaxStack": 1
      }
    }
  }
]
```

- [ ] **Step 4: Create sample_v2_multi.json fixture** (two objects of same type)

`tests/fixtures/sample_v2_multi.json`:
```json
[
  {
    "Type": "DCItemDataAsset",
    "Name": "Id_Item_A",
    "Properties": { "Item": { "MaxStack": 1 } }
  },
  {
    "Type": "DCItemDataAsset",
    "Name": "Id_Item_B",
    "Properties": { "Item": { "MaxStack": 99 } }
  }
]
```

- [ ] **Step 5: Commit**

```bash
git add tests/
git commit -m "test: add fixture files for core library tests"
```

---

### Task 3: core/reader.py — write failing tests first

**Files:**
- Create: `tests/core/test_reader.py`

- [ ] **Step 1: Write the failing tests**

`tests/core/test_reader.py`:
```python
"""Tests for pipeline/core/reader.py"""
import json
import pytest
from pathlib import Path
from pipeline.core.reader import load, find_files, find_by_type, get_properties, get_item

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_load_returns_list(tmp_path):
    f = tmp_path / "test.json"
    f.write_text('[{"Type": "Foo", "Name": "Bar"}]', encoding="utf-8")
    result = load(f)
    assert isinstance(result, list)
    assert result[0]["Type"] == "Foo"


def test_load_wraps_bare_object_in_list(tmp_path):
    """load() must return list[dict] even when JSON root is a bare object."""
    f = tmp_path / "bare.json"
    f.write_text('{"Type": "Foo"}', encoding="utf-8")
    result = load(f)
    assert isinstance(result, list)
    assert result[0]["Type"] == "Foo"


def test_load_raises_on_missing_file():
    with pytest.raises(FileNotFoundError):
        load(Path("/nonexistent/path/file.json"))


def test_load_raises_on_invalid_json(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("not json", encoding="utf-8")
    with pytest.raises(ValueError):
        load(f)


def test_find_files_finds_matching_files(tmp_path):
    (tmp_path / "a.json").write_text("[]", encoding="utf-8")
    (tmp_path / "b.json").write_text("[]", encoding="utf-8")
    (tmp_path / "c.txt").write_text("", encoding="utf-8")
    results = find_files(str(tmp_path / "*.json"))
    assert len(results) == 2
    assert all(p.suffix == ".json" for p in results)


def test_find_files_returns_sorted_paths(tmp_path):
    for name in ["c.json", "a.json", "b.json"]:
        (tmp_path / name).write_text("[]", encoding="utf-8")
    results = find_files(str(tmp_path / "*.json"))
    names = [p.name for p in results]
    assert names == sorted(names)


def test_find_files_returns_empty_list_for_no_matches(tmp_path):
    results = find_files(str(tmp_path / "*.json"))
    assert results == []


def test_find_by_type_returns_matching_files(tmp_path):
    f1 = tmp_path / "enum1.json"
    f1.write_text('[{"Type": "UserDefinedEnum", "Name": "E_Test"}]', encoding="utf-8")
    f2 = tmp_path / "other.json"
    f2.write_text('[{"Type": "Other", "Name": "X"}]', encoding="utf-8")
    results = find_by_type("UserDefinedEnum", tmp_path)
    assert len(results) == 1
    assert results[0].name == "enum1.json"


def test_get_properties_extracts_properties():
    obj = {"Type": "Foo", "Properties": {"A": 1, "B": 2}}
    assert get_properties(obj) == {"A": 1, "B": 2}


def test_get_properties_returns_empty_dict_on_missing():
    obj = {"Type": "Foo"}
    assert get_properties(obj) == {}


def test_get_item_extracts_item_struct():
    obj = {"Properties": {"Item": {"MaxStack": 5}}}
    assert get_item(obj) == {"MaxStack": 5}


def test_get_item_returns_empty_dict_on_missing():
    obj = {"Properties": {}}
    assert get_item(obj) == {}
```

- [ ] **Step 2: Run to verify tests fail (module not found)**

```bash
py -3 -m pytest tests/core/test_reader.py -v
```
Expected: `ModuleNotFoundError: No module named 'pipeline.core'`

---

### Task 4: core/reader.py — implement

**Files:**
- Create: `pipeline/core/__init__.py` (empty)
- Create: `pipeline/core/reader.py`

- [ ] **Step 1: Create pipeline/core/__init__.py**

Empty file.

- [ ] **Step 2: Implement pipeline/core/reader.py**

Note: The spec (§4.1) lists `glob(pattern)` in the interface. We name it `find_files` in the implementation to avoid shadowing the stdlib `glob` module. All internal callers use `find_files`; the spec name is treated as a conceptual label.

```python
"""Raw JSON loading and glob helpers for the extraction pipeline."""
import glob as _glob
import json
from pathlib import Path


def load(path: Path) -> list[dict]:
    """Parse one raw JSON file, returning a list of UE5 export objects."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}") from e
    return data if isinstance(data, list) else [data]


def find_files(pattern: str) -> list[Path]:
    """Find all files matching a glob pattern, returned sorted."""
    return sorted(Path(p) for p in _glob.glob(pattern, recursive=True))


def find_by_type(type_name: str, search_dir: Path) -> list[Path]:
    """Scan search_dir recursively for JSON files containing objects of the given Type."""
    results = []
    for json_file in sorted(Path(search_dir).rglob("*.json")):
        try:
            data = load(json_file)
        except (FileNotFoundError, ValueError):
            continue
        if any(isinstance(obj, dict) and obj.get("Type") == type_name for obj in data):
            results.append(json_file)
    return results


def get_properties(obj: dict) -> dict:
    """Safely extract obj['Properties'], returning {} if absent."""
    return obj.get("Properties") or {}


def get_item(obj: dict) -> dict:
    """Safely extract obj['Properties']['Item'], returning {} if absent."""
    return get_properties(obj).get("Item") or {}
```

- [ ] **Step 3: Run tests to verify they pass**

```bash
py -3 -m pytest tests/core/test_reader.py -v
```
Expected: all 12 tests PASS

- [ ] **Step 4: Commit**

```bash
git add pipeline/core/__init__.py pipeline/core/reader.py tests/core/test_reader.py
git commit -m "feat: add pipeline/core/reader.py with full test coverage"
```

---

## Chunk 2: Core Normalizer + Resolver

### File Map

- Create: `tests/core/test_normalizer.py`
- Create: `pipeline/core/normalizer.py`
- Create: `tests/core/test_resolver.py`
- Create: `pipeline/core/resolver.py`

---

### Task 5: core/normalizer.py — write failing tests

**Files:**
- Create: `tests/core/test_normalizer.py`

- [ ] **Step 1: Write the failing tests**

`tests/core/test_normalizer.py`:
```python
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
```

- [ ] **Step 2: Run to verify tests fail**

```bash
py -3 -m pytest tests/core/test_normalizer.py -v
```
Expected: `ModuleNotFoundError` or `ImportError`

---

### Task 6: core/normalizer.py — implement

**Files:**
- Create: `pipeline/core/normalizer.py`

- [ ] **Step 1: Implement pipeline/core/normalizer.py**

```python
"""UE5 → clean Python dict normalization helpers."""
import re
from typing import Any


def resolve_ref(value: Any) -> str | None:
    """{ ObjectName, ObjectPath } → asset_id string, or None if not a ref."""
    if isinstance(value, dict) and "ObjectName" in value and "ObjectPath" in value:
        return value["ObjectName"].split("'")[0]
    return None


def resolve_tag(value: Any) -> str | None:
    """{ TagName: 'X.Y.Z' } → 'X.Y.Z', or None if not a tag."""
    if isinstance(value, dict) and "TagName" in value:
        return value["TagName"]
    return None


def resolve_text(value: Any) -> str | None:
    """{ LocalizedString: '...' } → display string, or None if not a text."""
    if isinstance(value, dict) and "LocalizedString" in value:
        return value["LocalizedString"]
    return None


def camel_to_snake(key: str) -> str:
    """'MoveSpeedBase' → 'move_speed_base'"""
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", key)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def clean_flags(flags: str | None) -> list[str]:
    """'RF_Public | RF_Standalone' → ['Public', 'Standalone']"""
    if not flags:
        return []
    parts = [p.strip() for p in flags.split("|")]
    return [p.removeprefix("RF_") for p in parts if p]


def flatten(value: Any) -> Any:
    """Recursively resolve UE5 nested structs to clean Python values."""
    if value is None or isinstance(value, (bool, int, float)):
        return value

    if isinstance(value, str):
        return value

    if isinstance(value, list):
        return [flatten(item) for item in value]

    if isinstance(value, dict):
        # Try known UE5 patterns first (most specific to least)
        ref = resolve_ref(value)
        if ref is not None:
            return ref

        tag = resolve_tag(value)
        if tag is not None:
            return tag

        text = resolve_text(value)
        if text is not None:
            return text

        # Generic nested struct: recurse with snake_case keys
        return {camel_to_snake(k): flatten(v) for k, v in value.items()}

    return value
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
py -3 -m pytest tests/core/test_normalizer.py -v
```
Expected: all 16 tests PASS

- [ ] **Step 3: Commit**

```bash
git add pipeline/core/normalizer.py tests/core/test_normalizer.py
git commit -m "feat: add pipeline/core/normalizer.py with flatten/resolve helpers"
```

---

### Task 7: core/resolver.py — write failing tests

**Files:**
- Create: `tests/core/test_resolver.py`

- [ ] **Step 1: Write the failing tests**

`tests/core/test_resolver.py`:
```python
"""Tests for pipeline/core/resolver.py"""
import json
import pytest
from pathlib import Path
from pipeline.core.resolver import Resolver


@pytest.fixture
def resolver():
    return Resolver()


def test_register_and_resolve(resolver):
    resolver.register("items", "longsword", {"name": "Longsword"})
    result = resolver.resolve("longsword")
    assert result == {"name": "Longsword"}


def test_resolve_returns_none_for_unknown(resolver):
    assert resolver.resolve("unknown_asset") is None


def test_register_does_not_overwrite_existing(resolver):
    resolver.register("items", "sword", {"name": "Sword v1"})
    resolver.register("items", "sword", {"name": "Sword v2"})
    # Last write wins (register is idempotent for updates)
    assert resolver.resolve("sword")["name"] == "Sword v2"


def test_resolve_enum_returns_display_name(tmp_path, resolver):
    enums_data = {
        "E_DamageType": {
            "values": [
                {"index": 0, "name": "NewEnumerator0", "displayName": "Physical"},
                {"index": 1, "name": "NewEnumerator1", "displayName": "Magic"}
            ]
        }
    }
    enums_file = tmp_path / "enums.json"
    enums_file.write_text(json.dumps(enums_data), encoding="utf-8")
    resolver.load_enums(enums_file)
    assert resolver.resolve_enum("E_DamageType", 1) == "Magic"


def test_resolve_enum_returns_none_for_unknown_enum(resolver):
    assert resolver.resolve_enum("E_Unknown", 0) is None


def test_resolve_enum_returns_none_for_unknown_index(tmp_path, resolver):
    enums_data = {"E_Foo": {"values": [{"index": 0, "name": "A", "displayName": "Alpha"}]}}
    enums_file = tmp_path / "enums.json"
    enums_file.write_text(json.dumps(enums_data), encoding="utf-8")
    resolver.load_enums(enums_file)
    assert resolver.resolve_enum("E_Foo", 99) is None


def test_load_domain_hydrates_registry(tmp_path, resolver):
    domain_dir = tmp_path / "items"
    domain_dir.mkdir()
    sword = {"id": "sword", "name": "Sword"}
    (domain_dir / "sword.json").write_text(json.dumps(sword), encoding="utf-8")
    # _index.json should be skipped
    index = {"count": 1, "entries": []}
    (domain_dir / "_index.json").write_text(json.dumps(index), encoding="utf-8")
    resolver.load_domain("items", tmp_path)
    assert resolver.resolve("sword") == sword


def test_load_domain_skips_index_file(tmp_path, resolver):
    domain_dir = tmp_path / "items"
    domain_dir.mkdir()
    index = {"count": 0, "entries": []}
    (domain_dir / "_index.json").write_text(json.dumps(index), encoding="utf-8")
    resolver.load_domain("items", tmp_path)
    assert resolver.resolve("_index") is None


def test_concurrent_reads_are_safe(resolver):
    """register() from main thread, resolve() concurrent reads — no crash."""
    import threading
    resolver.register("items", "sword", {"name": "Sword"})
    errors = []

    def read_worker():
        try:
            for _ in range(100):
                resolver.resolve("sword")
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=read_worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
```

- [ ] **Step 2: Run to verify tests fail**

```bash
py -3 -m pytest tests/core/test_resolver.py -v
```
Expected: `ImportError` or `ModuleNotFoundError`

---

### Task 8: core/resolver.py — implement

**Files:**
- Create: `pipeline/core/resolver.py`

- [ ] **Step 1: Implement pipeline/core/resolver.py**

```python
"""Cross-domain ID linker and enum resolver."""
import json
import threading
from pathlib import Path


class Resolver:
    """
    Thread safety contract:
    - register() and load_domain() MUST be called from the main orchestrator thread only.
    - resolve() and resolve_enum() are safe to call concurrently from worker threads.
    """

    def __init__(self):
        self._registry: dict[str, dict] = {}
        self._enums: dict[str, dict] = {}
        self._lock = threading.Lock()

    def register(self, domain: str, id_: str, record: dict) -> None:
        """Add a record to the in-memory registry. Orchestrator-thread only."""
        with self._lock:
            self._registry[id_] = record

    def resolve(self, asset_id: str) -> dict | None:
        """Lookup a record by asset name or path. Safe to call from worker threads."""
        with self._lock:
            return self._registry.get(asset_id)

    def resolve_enum(self, enum_name: str, index: int) -> str | None:
        """Return displayName for enum_name at index, or None if not found."""
        enum = self._enums.get(enum_name)
        if not enum:
            return None
        for entry in enum.get("values", []):
            if entry.get("index") == index:
                return entry.get("displayName")
        return None

    def load_enums(self, enums_path: Path) -> None:
        """Load extracted/engine/enums.json into the enum lookup table."""
        with open(enums_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._enums = data

    def load_domain(self, domain: str, extracted_root: Path) -> None:
        """Hydrate registry from all entity files in extracted/<domain>/. Orchestrator-thread only.

        NOTE: Does NOT load enums. Call load_enums() separately for enum label resolution.
        The spec's 'resolver.load_domain("engine")' example refers to entity hydration only.
        """
        domain_dir = extracted_root / domain
        if not domain_dir.exists():
            return
        for json_file in sorted(domain_dir.glob("*.json")):
            if json_file.name.startswith("_"):
                continue
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    record = json.load(f)
                entity_id = json_file.stem
                self.register(domain, entity_id, record)
            except (json.JSONDecodeError, IOError):
                continue
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
py -3 -m pytest tests/core/test_resolver.py -v
```
Expected: all 9 tests PASS

- [ ] **Step 3: Commit**

```bash
git add pipeline/core/resolver.py tests/core/test_resolver.py
git commit -m "feat: add pipeline/core/resolver.py with thread-safe registry"
```

---

## Chunk 3: Core Writer + Analyzer

### File Map

- Create: `tests/core/test_writer.py`
- Create: `pipeline/core/writer.py`
- Create: `tests/core/test_analyzer.py`
- Create: `pipeline/core/analyzer.py`

---

### Task 9: core/writer.py — write failing tests

**Files:**
- Create: `tests/core/test_writer.py`

- [ ] **Step 1: Write the failing tests**

`tests/core/test_writer.py`:
```python
"""Tests for pipeline/core/writer.py"""
import json
import pytest
from pathlib import Path
from pipeline.core.writer import Writer

PIPELINE_VERSION = "1.0.0"


@pytest.fixture
def writer(tmp_path):
    return Writer(extracted_root=tmp_path, pipeline_version=PIPELINE_VERSION)


def test_write_entity_creates_file(writer, tmp_path):
    writer.write_entity("items", "sword", {"id": "sword", "name": "Sword"}, source_files=["raw/x.json"])
    out = tmp_path / "items" / "sword.json"
    assert out.exists()


def test_write_entity_adds_meta(writer, tmp_path):
    writer.write_entity("items", "sword", {"id": "sword"}, source_files=["raw/x.json"])
    data = json.loads((tmp_path / "items" / "sword.json").read_text(encoding="utf-8"))
    assert "_meta" in data
    assert data["_meta"]["pipeline_version"] == PIPELINE_VERSION
    assert isinstance(data["_meta"]["source_files"], list)
    assert "raw/x.json" in data["_meta"]["source_files"]
    assert "extracted_at" in data["_meta"]


def test_write_entity_meta_is_last_key(writer, tmp_path):
    writer.write_entity("items", "sword", {"id": "sword", "name": "X"}, source_files=[])
    data = json.loads((tmp_path / "items" / "sword.json").read_text(encoding="utf-8"))
    assert list(data.keys())[-1] == "_meta"


def test_write_index_creates_index_file(writer, tmp_path):
    entries = [{"id": "sword", "name": "Sword"}]
    writer.write_index("items", entries)
    out = tmp_path / "items" / "_index.json"
    assert out.exists()


def test_write_index_structure(writer, tmp_path):
    entries = [{"id": "a"}, {"id": "b"}]
    writer.write_index("items", entries)
    data = json.loads((tmp_path / "items" / "_index.json").read_text(encoding="utf-8"))
    assert data["count"] == 2
    assert data["entries"] == entries
    assert "_meta" in data


def test_write_system_creates_file(writer, tmp_path):
    writer.write_system("engine", "curves", {"data": 123}, source_files=["raw/ct.json"])
    out = tmp_path / "engine" / "curves.json"
    assert out.exists()


def test_write_system_adds_meta(writer, tmp_path):
    writer.write_system("engine", "curves", {"data": 123}, source_files=["raw/a.json", "raw/b.json"])
    data = json.loads((tmp_path / "engine" / "curves.json").read_text(encoding="utf-8"))
    assert data["_meta"]["source_files"] == ["raw/a.json", "raw/b.json"]


def test_creates_domain_directory_if_missing(writer, tmp_path):
    writer.write_entity("newdomain", "thing", {"id": "thing"}, source_files=[])
    assert (tmp_path / "newdomain").is_dir()
```

- [ ] **Step 2: Run to verify tests fail**

```bash
py -3 -m pytest tests/core/test_writer.py -v
```
Expected: `ImportError`

---

### Task 10: core/writer.py — implement

**Files:**
- Create: `pipeline/core/writer.py`

- [ ] **Step 1: Implement pipeline/core/writer.py**

```python
"""Standardized output writers for the extraction pipeline."""
import json
from datetime import datetime, timezone
from pathlib import Path


class Writer:
    def __init__(self, extracted_root: Path, pipeline_version: str = "1.0.0"):
        self.extracted_root = Path(extracted_root)
        self.pipeline_version = pipeline_version

    def _meta(self, source_files: list[str]) -> dict:
        return {
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "source_files": list(source_files),
            "pipeline_version": self.pipeline_version,
        }

    def _write(self, path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def write_entity(self, domain: str, id_: str, data: dict, source_files: list[str]) -> Path:
        """Write extracted/<domain>/<id>.json with _meta appended."""
        out = {k: v for k, v in data.items() if k != "_meta"}
        out["_meta"] = self._meta(source_files)
        path = self.extracted_root / domain / f"{id_}.json"
        self._write(path, out)
        return path

    def write_index(self, domain: str, entries: list[dict]) -> Path:
        """Write extracted/<domain>/_index.json."""
        data = {
            "count": len(entries),
            "entries": entries,
            "_meta": self._meta([]),
        }
        path = self.extracted_root / domain / "_index.json"
        self._write(path, data)
        return path

    def write_system(self, domain: str, name: str, data: dict, source_files: list[str]) -> Path:
        """Write extracted/<domain>/<name>.json for non-entity system files."""
        out = {k: v for k, v in data.items() if k != "_meta"}
        out["_meta"] = self._meta(source_files)
        path = self.extracted_root / domain / f"{name}.json"
        self._write(path, out)
        return path
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
py -3 -m pytest tests/core/test_writer.py -v
```
Expected: all 8 tests PASS

- [ ] **Step 3: Commit**

```bash
git add pipeline/core/writer.py tests/core/test_writer.py
git commit -m "feat: add pipeline/core/writer.py with entity/index/system writers"
```

---

### Task 11: core/analyzer.py — write failing tests

**Files:**
- Create: `tests/core/test_analyzer.py`

- [ ] **Step 1: Write the failing tests**

`tests/core/test_analyzer.py`:
```python
"""Tests for pipeline/core/analyzer.py"""
from pipeline.core.analyzer import dps, drop_rate_pct, speed_at_base, add_notes, add_formula


def test_dps_calculation():
    assert abs(dps(40, 1.0) - 40.0) < 0.001
    assert abs(dps(40, 2.0) - 20.0) < 0.001


def test_dps_handles_zero_speed():
    assert dps(40, 0) == 0.0


def test_drop_rate_pct_calculation():
    result = drop_rate_pct(1, 4)
    assert abs(result - 25.0) < 0.001


def test_drop_rate_pct_handles_zero_total():
    assert drop_rate_pct(1, 0) == 0.0


def test_speed_at_base_applies_multiplier():
    assert abs(speed_at_base(0.65) - 195.0) < 0.001


def test_speed_at_base_custom_base():
    assert abs(speed_at_base(0.5, base=200) - 100.0) < 0.001


def test_add_notes_injects_list():
    data = {"id": "sword"}
    result = add_notes(data, ["note one", "note two"])
    assert result["_analysis_notes"] == ["note one", "note two"]


def test_add_notes_appends_to_existing():
    data = {"_analysis_notes": ["existing"]}
    result = add_notes(data, ["new note"])
    assert result["_analysis_notes"] == ["existing", "new note"]


def test_add_notes_returns_data():
    data = {"id": "x"}
    result = add_notes(data, ["n"])
    assert result is data


def test_add_formula_injects_formula():
    data = {"id": "x"}
    add_formula(data, "final_damage", "(base + bonus) * scale", "medium", ["caveat 1"])
    assert "_formulas" in data
    assert data["_formulas"][0]["name"] == "final_damage"
    assert data["_formulas"][0]["confidence"] == "medium"
    assert data["_formulas"][0]["caveats"] == ["caveat 1"]


def test_add_formula_appends_to_existing():
    data = {"_formulas": [{"name": "f1"}]}
    add_formula(data, "f2", "expr", "confirmed", [])
    assert len(data["_formulas"]) == 2
```

- [ ] **Step 2: Run to verify tests fail**

```bash
py -3 -m pytest tests/core/test_analyzer.py -v
```
Expected: `ImportError`

---

### Task 12: core/analyzer.py — implement

**Files:**
- Create: `pipeline/core/analyzer.py`

- [ ] **Step 1: Implement pipeline/core/analyzer.py**

```python
"""Derived field calculators and analysis note helpers."""


def dps(damage: float, speed: float) -> float:
    """Compute DPS = damage / attack_interval. speed=0 → 0.0."""
    if speed == 0:
        return 0.0
    return round(damage / speed, 4)


def drop_rate_pct(weight: float, total: float) -> float:
    """Compute drop rate as percentage. total=0 → 0.0."""
    if total == 0:
        return 0.0
    return round((weight / total) * 100, 4)


def speed_at_base(multiplier: float, base: float = 300) -> float:
    """Compute effective speed = base * multiplier."""
    return round(base * multiplier, 4)


def add_notes(data: dict, notes: list[str]) -> dict:
    """Inject or append to _analysis_notes list in data. Returns data."""
    existing = data.get("_analysis_notes", [])
    data["_analysis_notes"] = existing + list(notes)
    return data


def add_formula(data: dict, name: str, expression: str,
                confidence: str, caveats: list[str]) -> dict:
    """Inject or append a formula entry into _formulas list. Returns data."""
    entry = {
        "name": name,
        "expression": expression,
        "confidence": confidence,
        "caveats": list(caveats),
    }
    data.setdefault("_formulas", []).append(entry)
    return data
```

- [ ] **Step 2: Run all core tests together**

```bash
py -3 -m pytest tests/core/ -v
```
Expected: all tests PASS (30+ tests)

- [ ] **Step 3: Commit**

```bash
git add pipeline/core/analyzer.py tests/core/test_analyzer.py
git commit -m "feat: add pipeline/core/analyzer.py with dps/drop_rate/notes helpers"
```

---

## Chunk 4: Engine Domain + Cleanup

### File Map

- Create: `tests/domains/__init__.py`
- Create: `tests/domains/engine/__init__.py`
- Create: `tests/domains/engine/test_extract_enums.py`
- Create: `pipeline/domains/__init__.py`
- Create: `pipeline/domains/engine/__init__.py`
- Create: `pipeline/domains/engine/extract_enums.py`
- Create: `pipeline/domains/engine/extract_constants.py`
- Create: `pipeline/domains/engine/extract_curves.py`
- Create: `pipeline/domains/engine/extract_tags.py`
- Modify: `pipeline/utils.py` (add re-exports of core/)
- Delete: `pipeline/extract_classes.py`, `pipeline/extract_economy.py`, `pipeline/extract_engine.py`, `pipeline/extract_gameplay.py`, `pipeline/extract_items.py`, `pipeline/extract_maps.py`, `pipeline/extract_monsters.py`, `pipeline/extract_enums.py` (superseded by domain version)

---

### Task 13: engine/extract_enums.py (migrate from pipeline/extract_enums.py)

> **Deliberate deviation from spec §2.1:** Spec says `pipeline/extract_enums.py` is "kept unchanged". However, since the domain run() must produce enums, keeping both files produces two extractors writing the same output. This plan migrates the logic into `domains/engine/extract_enums.py` and **deletes** the standalone `pipeline/extract_enums.py` in Task 18. The canonical output (`extracted/engine/enums.json`) is identical in format.

**Files:**
- Create: `tests/domains/__init__.py` (empty)
- Create: `tests/domains/engine/__init__.py` (empty)
- Create: `tests/domains/engine/test_extract_enums.py`
- Create: `pipeline/domains/__init__.py` (empty)
- Create: `pipeline/domains/engine/__init__.py`
- Create: `pipeline/domains/engine/extract_enums.py`

- [ ] **Step 1: Create domain test directory**

```bash
mkdir -p darkanddarker-wiki/tests/domains/engine
touch darkanddarker-wiki/tests/domains/__init__.py
touch darkanddarker-wiki/tests/domains/engine/__init__.py
mkdir -p darkanddarker-wiki/pipeline/domains/engine
touch darkanddarker-wiki/pipeline/domains/__init__.py
touch darkanddarker-wiki/pipeline/domains/engine/__init__.py
```

- [ ] **Step 2: Write the failing tests**

`tests/domains/engine/test_extract_enums.py`:
```python
"""Tests for pipeline/domains/engine/extract_enums.py"""
import json
import pytest
from pathlib import Path
from pipeline.domains.engine.extract_enums import extract_enum_from_file, run_enums


FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


def make_enum_file(tmp_path, name, names_dict, display_map=None):
    """Helper: write a UserDefinedEnum JSON file."""
    display_map = display_map or []
    data = [{
        "Type": "UserDefinedEnum",
        "Name": name,
        "Names": names_dict,
        "Properties": {"DisplayNameMap": display_map}
    }]
    f = tmp_path / f"{name}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_enum_returns_name_and_values(tmp_path):
    f = make_enum_file(tmp_path, "E_Foo", {"E_Foo::Val0": 0, "E_Foo::Val1": 1, "E_Foo::_MAX": 2})
    result = extract_enum_from_file(f)
    assert result["name"] == "E_Foo"
    assert len(result["values"]) == 2  # _MAX excluded


def test_extract_enum_uses_display_names(tmp_path):
    display_map = [
        {"Key": "Val0", "Value": {"CultureInvariantString": "Zero"}},
        {"Key": "Val1", "Value": {"CultureInvariantString": "One"}},
    ]
    f = make_enum_file(tmp_path, "E_Bar",
                       {"E_Bar::Val0": 0, "E_Bar::Val1": 1, "E_Bar::_MAX": 2},
                       display_map)
    result = extract_enum_from_file(f)
    by_index = {v["index"]: v["displayName"] for v in result["values"]}
    assert by_index[0] == "Zero"
    assert by_index[1] == "One"


def test_extract_enum_sorts_by_index(tmp_path):
    f = make_enum_file(tmp_path, "E_Baz", {"E_Baz::C": 2, "E_Baz::A": 0, "E_Baz::B": 1})
    result = extract_enum_from_file(f)
    indices = [v["index"] for v in result["values"]]
    assert indices == sorted(indices)


def test_extract_enum_returns_none_for_non_enum(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "Other", "Name": "Foo"}]', encoding="utf-8")
    assert extract_enum_from_file(f) is None


def test_run_enums_writes_output(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    make_enum_file(raw_dir, "E_Test", {"E_Test::A": 0, "E_Test::_MAX": 1})
    extracted_dir = tmp_path / "extracted"
    run_enums(raw_dir=raw_dir, extracted_root=extracted_dir)
    out = extracted_dir / "engine" / "enums.json"
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "E_Test" in data
```

- [ ] **Step 3: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/engine/test_extract_enums.py -v
```
Expected: `ImportError`

- [ ] **Step 4: Implement pipeline/domains/engine/extract_enums.py**

```python
"""Extract UserDefinedEnum assets from raw/ → extracted/engine/enums.json."""
import json
import sys
from pathlib import Path

from pipeline.core.reader import find_by_type, load
from pipeline.core.writer import Writer


def extract_enum_from_file(file_path: Path) -> dict | None:
    """Extract enum name and values from a UserDefinedEnum file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return None

    enum_obj = next((obj for obj in data
                     if isinstance(obj, dict) and obj.get("Type") == "UserDefinedEnum"), None)
    if not enum_obj:
        return None

    enum_name = enum_obj.get("Name")
    if not enum_name:
        return None

    # Build display name lookup from DisplayNameMap
    display_names = {}
    for entry in enum_obj.get("Properties", {}).get("DisplayNameMap", []):
        key = entry.get("Key")
        val = entry.get("Value", {}).get("CultureInvariantString", "")
        if key:
            display_names[key] = val

    # Extract enum values, skip _MAX sentinel
    values = []
    for full_name, index in enum_obj.get("Names", {}).items():
        if full_name.endswith("_MAX"):
            continue
        parts = full_name.split("::")
        if len(parts) == 2:
            member = parts[1]
            values.append({
                "index": index,
                "name": member,
                "displayName": display_names.get(member, member),
            })

    values.sort(key=lambda v: v["index"])
    return {"name": enum_name, "values": values}


def run_enums(raw_dir: Path, extracted_root: Path) -> dict:
    """Extract all UserDefinedEnum files. Returns {enum_name: {values: [...]}}."""
    print(f"  [enums] Scanning {raw_dir}...")
    enum_files = find_by_type("UserDefinedEnum", raw_dir)
    print(f"  [enums] Found {len(enum_files)} enum files")

    enums_data = {}
    for file_path in enum_files:
        result = extract_enum_from_file(file_path)
        if result:
            enums_data[result["name"]] = {"values": result["values"]}

    writer = Writer(extracted_root)
    # enums.json is a system file (not entity-per-enum)
    writer.write_system("engine", "enums", enums_data,
                        source_files=[str(f) for f in enum_files])
    print(f"  [enums] Extracted {len(enums_data)} enums")
    return enums_data
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/engine/test_extract_enums.py -v
```
Expected: all 5 tests PASS

- [ ] **Step 6: Commit**

```bash
git add pipeline/domains/ tests/domains/
git commit -m "feat: add domains/engine/extract_enums.py migrated to core/ library"
```

---

### Task 14: engine/extract_constants.py

**Files:**
- Create: `pipeline/domains/engine/extract_constants.py`

Constants are `V2/Constant/Constant/Id_Constant_*.json` files. Each has a `Properties.Item.ConstantValue` (float or int) and `Properties.Item.ConstantId` (asset ref).

- [ ] **Step 1: Explore a sample constant file to confirm structure**

```bash
py -3 -c "
import json
from pathlib import Path
raw = Path('raw/DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/Constant/Constant')
files = sorted(raw.glob('*.json'))[:3]
for f in files:
    data = json.loads(f.read_text(encoding='utf-8'))
    print(f.name, '->', data[0].get('Properties', {}).get('Item', {}).keys())
"
```
Expected output: shows `ConstantId`, `ConstantValue` keys in Item

- [ ] **Step 2: Write the failing tests**

`tests/domains/engine/test_extract_constants.py`:
```python
"""Tests for pipeline/domains/engine/extract_constants.py"""
import json
import pytest
from pathlib import Path
from pipeline.domains.engine.extract_constants import extract_constant, run_constants


def make_constant_file(tmp_path, const_name, value):
    data = [{
        "Type": "DCConstantDataAsset",
        "Name": const_name,
        "Properties": {
            "Item": {
                "ConstantId": {
                    "ObjectName": f"{const_name}'...'",
                    "ObjectPath": f"/Game/Data/{const_name}.0"
                },
                "ConstantValue": value
            }
        }
    }]
    f = tmp_path / f"{const_name}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_constant_returns_id_and_value(tmp_path):
    f = make_constant_file(tmp_path, "Id_Constant_CharacterBaseMoveSpeed", 300.0)
    result = extract_constant(f)
    assert result is not None
    assert result["id"] == "Id_Constant_CharacterBaseMoveSpeed"
    assert result["value"] == 300.0


def test_extract_constant_returns_none_for_non_constant(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "Other"}]', encoding="utf-8")
    assert extract_constant(f) is None


def test_run_constants_writes_system_file(tmp_path):
    raw_dir = tmp_path / "raw" / "V2" / "Constant" / "Constant"
    raw_dir.mkdir(parents=True)
    make_constant_file(raw_dir, "Id_Constant_MaxMoveSpeed", 330.0)
    extracted = tmp_path / "extracted"
    run_constants(raw_dir=raw_dir, extracted_root=extracted)
    out = extracted / "engine" / "constants.json"
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "constants" in data
```

- [ ] **Step 3: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/engine/test_extract_constants.py -v
```
Expected: `ImportError`

- [ ] **Step 4: Implement pipeline/domains/engine/extract_constants.py**

```python
"""Extract V2/Constant assets → extracted/engine/constants.json."""
import sys
from pathlib import Path

from pipeline.core.reader import load, get_item
from pipeline.core.normalizer import resolve_ref
from pipeline.core.writer import Writer


def extract_constant(file_path: Path) -> dict | None:
    """Extract one constant from a DCConstantDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and "Constant" in o.get("Type", "")), None)
    if not obj:
        return None

    item = get_item(obj)
    const_id_ref = item.get("ConstantId")
    const_id = resolve_ref(const_id_ref) if const_id_ref else obj.get("Name", "")
    value = item.get("ConstantValue")

    return {
        "id": const_id or file_path.stem,
        "value": value,
        "source_file": str(file_path),
    }


def run_constants(raw_dir: Path, extracted_root: Path) -> dict:
    """Extract all Constant files → extracted/engine/constants.json."""
    print(f"  [constants] Scanning {raw_dir}...")
    files = sorted(raw_dir.glob("Id_Constant_*.json"))
    print(f"  [constants] Found {len(files)} constant files")

    constants = {}
    source_files = []
    for f in files:
        result = extract_constant(f)
        if result:
            constants[result["id"]] = result["value"]
            source_files.append(result["source_file"])

    writer = Writer(extracted_root)
    writer.write_system("engine", "constants", {"constants": constants},
                        source_files=source_files)
    print(f"  [constants] Extracted {len(constants)} constants")
    return constants
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/engine/test_extract_constants.py -v
```
Expected: all 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add pipeline/domains/engine/extract_constants.py tests/domains/engine/test_extract_constants.py
git commit -m "feat: add domains/engine/extract_constants.py"
```

---

### Task 15: engine/extract_curves.py

CT_ curve tables live at `raw/.../Data/GameplayAbility/CT_*.json`. Each has `Type: "CurveTable"`, `CurveTableMode: "SimpleCurves"`, and `Rows: { "AttributeName": { "InterpMode": "...", "Keys": [{Time, Value}] } }`.

Standalone `CurveFloat` assets (`Type: "CurveFloat"`) are a separate UE5 type with structure `{"FloatCurve": {"Keys": [{"Time": ..., "Value": ...}]}}`. Both types are extracted to `extracted/engine/curves.json` — CT_ tables under `curve_tables` key, CurveFloat under `curve_floats` key.

**Files:**
- Create: `pipeline/domains/engine/extract_curves.py`
- Create: `tests/domains/engine/test_extract_curves.py`

- [ ] **Step 1: Write the failing tests**

`tests/domains/engine/test_extract_curves.py`:
```python
"""Tests for pipeline/domains/engine/extract_curves.py"""
import json
import pytest
from pathlib import Path
from pipeline.domains.engine.extract_curves import extract_curve_table, run_curves


def make_curve_file(tmp_path, name, rows):
    data = [{
        "Type": "CurveTable",
        "Name": name,
        "CurveTableMode": "SimpleCurves",
        "Rows": rows
    }]
    f = tmp_path / f"{name}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_curve_table_returns_name_and_rows(tmp_path):
    rows = {
        "ActionSpeed": {
            "InterpMode": "RCIM_Linear",
            "Keys": [{"Time": 0, "Value": -0.38}, {"Time": 15, "Value": 0.0}]
        }
    }
    f = make_curve_file(tmp_path, "CT_ActionSpeed", rows)
    result = extract_curve_table(f)
    assert result["name"] == "CT_ActionSpeed"
    assert "ActionSpeed" in result["rows"]
    assert len(result["rows"]["ActionSpeed"]["keys"]) == 2


def test_extract_curve_table_returns_none_for_non_curve(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "Other"}]', encoding="utf-8")
    assert extract_curve_table(f) is None


def make_curve_float_file(tmp_path, name, keys):
    data = [{
        "Type": "CurveFloat",
        "Name": name,
        "Properties": {
            "FloatCurve": {
                "Keys": keys
            }
        }
    }]
    f = tmp_path / f"{name}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_run_curves_writes_system_file(tmp_path):
    raw_dir = tmp_path / "ga_dir"
    raw_dir.mkdir()
    make_curve_file(raw_dir, "CT_Agility", {
        "MoveSpeedBase": {"InterpMode": "RCIM_Linear", "Keys": [{"Time": 0, "Value": 0}]}
    })
    extracted = tmp_path / "extracted"
    run_curves(curve_dirs=[raw_dir], extracted_root=extracted)
    out = extracted / "engine" / "curves.json"
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "CT_Agility" in data["curve_tables"]


def test_extract_curve_float_returns_name_and_keys(tmp_path):
    f = make_curve_float_file(tmp_path, "CF_DamageFalloff",
                              [{"Time": 0.0, "Value": 1.0}, {"Time": 100.0, "Value": 0.5}])
    from pipeline.domains.engine.extract_curves import extract_curve_float
    result = extract_curve_float(f)
    assert result["name"] == "CF_DamageFalloff"
    assert len(result["keys"]) == 2


def test_run_curves_includes_curve_floats(tmp_path):
    raw_dir = tmp_path / "ga_dir"
    raw_dir.mkdir()
    make_curve_float_file(raw_dir, "CF_Test", [{"Time": 0.0, "Value": 1.0}])
    extracted = tmp_path / "extracted"
    run_curves(curve_dirs=[raw_dir], extracted_root=extracted)
    data = json.loads((extracted / "engine" / "curves.json").read_text(encoding="utf-8"))
    assert "CF_Test" in data["curve_floats"]
```

- [ ] **Step 2: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/engine/test_extract_curves.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement pipeline/domains/engine/extract_curves.py**

```python
"""Extract CT_ CurveTable and CurveFloat assets → extracted/engine/curves.json."""
import sys
from pathlib import Path

from pipeline.core.reader import load
from pipeline.core.writer import Writer


def extract_curve_table(file_path: Path) -> dict | None:
    """Extract one CT_ CurveTable into normalized form."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "CurveTable"), None)
    if not obj:
        return None

    rows = {}
    for attr_name, curve in (obj.get("Rows") or {}).items():
        keys = [{"time": k["Time"], "value": k["Value"]}
                for k in (curve.get("Keys") or [])]
        rows[attr_name] = {
            "interp_mode": curve.get("InterpMode", "RCIM_Linear"),
            "keys": keys,
        }

    return {
        "name": obj.get("Name", file_path.stem),
        "rows": rows,
        "source_file": str(file_path),
    }


def extract_curve_float(file_path: Path) -> dict | None:
    """Extract one CurveFloat asset into normalized form."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "CurveFloat"), None)
    if not obj:
        return None

    raw_keys = (obj.get("Properties", {}).get("FloatCurve") or {}).get("Keys", [])
    keys = [{"time": k.get("Time", 0), "value": k.get("Value", 0)} for k in raw_keys]

    return {
        "name": obj.get("Name", file_path.stem),
        "keys": keys,
        "source_file": str(file_path),
    }


def run_curves(curve_dirs: list[Path], extracted_root: Path) -> dict:
    """Extract CT_ curve tables and CurveFloat assets → extracted/engine/curves.json."""
    curve_tables = {}
    curve_floats = {}
    source_files = []

    for curve_dir in curve_dirs:
        ct_files = sorted(Path(curve_dir).glob("CT_*.json"))
        print(f"  [curves] Found {len(ct_files)} CT_ files in {curve_dir}")
        for f in ct_files:
            result = extract_curve_table(f)
            if result:
                curve_tables[result["name"]] = {"rows": result["rows"]}
                source_files.append(result["source_file"])

        # CurveFloat assets may appear alongside CT_ tables or in other dirs
        for f in sorted(Path(curve_dir).rglob("*.json")):
            result = extract_curve_float(f)
            if result:
                curve_floats[result["name"]] = {"keys": result["keys"]}
                source_files.append(result["source_file"])

    writer = Writer(extracted_root)
    writer.write_system("engine", "curves",
                        {"curve_tables": curve_tables, "curve_floats": curve_floats},
                        source_files=source_files)
    print(f"  [curves] Extracted {len(curve_tables)} curve tables, {len(curve_floats)} curve floats")
    return {"curve_tables": curve_tables, "curve_floats": curve_floats}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/engine/test_extract_curves.py -v
```
Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/engine/extract_curves.py tests/domains/engine/test_extract_curves.py
git commit -m "feat: add domains/engine/extract_curves.py for CT_ curve tables and CurveFloat assets"
```

---

### Task 16: engine/extract_tags.py

Tag group assets (`IdTagGroup`, `AbilityRelationshipTagGroup`, `GameplayCueTagGroup`, `GameplayEffectRelationTagGroup`, `TagMessageRelationshipTagGroup`, `InteractSettingGroup`) define gameplay tag hierarchies. Each file contains a list of tag entries.

**Files:**
- Create: `pipeline/domains/engine/extract_tags.py`
- Create: `tests/domains/engine/test_extract_tags.py`

- [ ] **Step 1: Explore a tag group file**

```bash
py -3 -c "
import json
from pathlib import Path
raw = Path('raw/DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/IdTagGroup')
files = list(raw.rglob('*.json'))
if files:
    data = json.loads(files[0].read_text(encoding='utf-8'))
    print(files[0].name)
    print(list(data[0].keys()))
    print(list(data[0].get('Properties', {}).keys()))
"
```

- [ ] **Step 2: Write the failing tests**

`tests/domains/engine/test_extract_tags.py`:
```python
"""Tests for pipeline/domains/engine/extract_tags.py"""
import json
import pytest
from pathlib import Path
from pipeline.domains.engine.extract_tags import run_tags


def make_tag_file(tmp_path, name, tag_type, tags):
    data = [{
        "Type": tag_type,
        "Name": name,
        "Properties": {"Tags": tags}
    }]
    f = tmp_path / f"{name}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_run_tags_writes_output(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    make_tag_file(raw_dir, "Id_TagGroup_Test", "IdTagGroup",
                  [{"TagName": "State.Test.Active"}])
    extracted = tmp_path / "extracted"
    run_tags(raw_dirs=[raw_dir], extracted_root=extracted)
    out = extracted / "engine" / "tags.json"
    assert out.exists()


def test_run_tags_groups_by_type(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    make_tag_file(raw_dir, "Id_TagGroup_Combat", "IdTagGroup",
                  [{"TagName": "State.Combat.Active"}])
    make_tag_file(raw_dir, "Id_CueGroup_Hit", "GameplayCueTagGroup",
                  [{"TagName": "GameplayCue.Hit"}])
    extracted = tmp_path / "extracted"
    run_tags(raw_dirs=[raw_dir], extracted_root=extracted)
    data = json.loads((extracted / "engine" / "tags.json").read_text(encoding="utf-8"))
    assert "id_tag_groups" in data
    assert "gameplay_cue_tag_groups" in data
```

- [ ] **Step 3: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/engine/test_extract_tags.py -v
```
Expected: `ImportError`

- [ ] **Step 4: Implement pipeline/domains/engine/extract_tags.py**

```python
"""Extract tag group assets → extracted/engine/tags.json."""
import sys
from pathlib import Path

from pipeline.core.reader import load
from pipeline.core.normalizer import camel_to_snake
from pipeline.core.writer import Writer

# Map UE5 Type → output key
TAG_TYPE_MAP = {
    "IdTagGroup": "id_tag_groups",
    "AbilityRelationshipTagGroup": "ability_relationship_tag_groups",
    "GameplayCueTagGroup": "gameplay_cue_tag_groups",
    "GameplayEffectRelationTagGroup": "gameplay_effect_relation_tag_groups",
    "TagMessageRelationshipTagGroup": "tag_message_relationship_tag_groups",
    "InteractSettingGroup": "interact_setting_groups",
}


def run_tags(raw_dirs: list[Path], extracted_root: Path) -> dict:
    """Extract all tag group assets → extracted/engine/tags.json."""
    groups: dict[str, list] = {v: [] for v in TAG_TYPE_MAP.values()}
    source_files = []

    for raw_dir in raw_dirs:
        for json_file in sorted(Path(raw_dir).rglob("*.json")):
            try:
                data = load(json_file)
            except (FileNotFoundError, ValueError):
                continue
            for obj in data:
                type_name = obj.get("Type", "")
                output_key = TAG_TYPE_MAP.get(type_name)
                if not output_key:
                    continue
                tags = obj.get("Properties", {}).get("Tags", [])
                tag_names = [t.get("TagName", t) if isinstance(t, dict) else t for t in tags]
                groups[output_key].append({
                    "name": obj.get("Name", ""),
                    "tags": tag_names,
                    "source_file": str(json_file),
                })
                source_files.append(str(json_file))
                break  # one tag group per file

    writer = Writer(extracted_root)
    writer.write_system("engine", "tags", groups, source_files=source_files)
    total = sum(len(v) for v in groups.values())
    print(f"  [tags] Extracted {total} tag group entries")
    return groups
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/engine/test_extract_tags.py -v
```
Expected: all 2 tests PASS

- [ ] **Step 6: Commit**

```bash
git add pipeline/domains/engine/extract_tags.py tests/domains/engine/test_extract_tags.py
git commit -m "feat: add domains/engine/extract_tags.py for tag group assets"
```

---

### Task 17: domains/engine/__init__.py — run() entry point

**Files:**
- Modify: `pipeline/domains/engine/__init__.py`

- [ ] **Step 1: Implement the run() entry point**

`pipeline/domains/engine/__init__.py`:
```python
"""Engine domain extractor — run() called by extract_all.py orchestrator."""
from pathlib import Path

from pipeline.domains.engine.extract_enums import run_enums
from pipeline.domains.engine.extract_constants import run_constants
from pipeline.domains.engine.extract_curves import run_curves
from pipeline.domains.engine.extract_tags import run_tags

# Standard V2 directories for engine systems
_V2_BASE = "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2"
_GA_BASE = "DungeonCrawler/Content/DungeonCrawler/Data/GameplayAbility"

TAG_TYPES = [
    "IdTagGroup", "AbilityRelationshipTagGroup", "GameplayCueTagGroup",
    "GameplayEffectRelationTagGroup", "TagMessageRelationshipTagGroup",
    "InteractSettingGroup",
]


def run(raw_root: Path, extracted_root: Path) -> dict:
    """Run all engine domain extractors. Returns summary of file counts."""
    print("[engine] Starting extraction...")
    summary = {}

    # Enums — scans entire raw_root (not a V2 subpath) because UserDefinedEnum
    # files are scattered across raw/ outside the V2 tree (spec §3).
    enums = run_enums(
        raw_dir=raw_root,
        extracted_root=extracted_root,
    )
    summary["enums"] = len(enums)

    # Constants
    constants_dir = raw_root / _V2_BASE / "Constant" / "Constant"
    if constants_dir.exists():
        consts = run_constants(raw_dir=constants_dir, extracted_root=extracted_root)
        summary["constants"] = len(consts)
    else:
        print(f"  [constants] WARNING: {constants_dir} not found, skipping")
        summary["constants"] = 0

    # Curve tables
    ga_dir = raw_root / _GA_BASE
    curve_dirs = [ga_dir] if ga_dir.exists() else []
    curves = run_curves(curve_dirs=curve_dirs, extracted_root=extracted_root)
    summary["curve_tables"] = len(curves["curve_tables"])
    summary["curve_floats"] = len(curves["curve_floats"])

    # Tag groups
    tag_dirs = []
    for tag_type in TAG_TYPES:
        d = raw_root / _V2_BASE / tag_type
        if d.exists():
            tag_dirs.append(d)
    run_tags(raw_dirs=tag_dirs, extracted_root=extracted_root)
    summary["tag_dirs_scanned"] = len(tag_dirs)

    print(f"[engine] Done. Summary: {summary}")
    return summary
```

- [ ] **Step 2: Write a smoke test for run()**

Add to `tests/domains/engine/test_extract_enums.py` or create a new file `tests/domains/engine/test_engine_run.py`:

```python
"""Smoke test for engine domain run() function."""
import json
from pathlib import Path
from pipeline.domains.engine import run


def test_engine_run_smoke(tmp_path):
    """run() completes without error even on empty raw dirs."""
    raw = tmp_path / "raw"
    raw.mkdir()
    extracted = tmp_path / "extracted"
    summary = run(raw_root=raw, extracted_root=extracted)
    assert isinstance(summary, dict)
    assert "enums" in summary
```

- [ ] **Step 3: Run the smoke test**

```bash
py -3 -m pytest tests/domains/engine/test_engine_run.py -v
```
Expected: PASS

- [ ] **Step 4: Run full engine domain tests**

```bash
py -3 -m pytest tests/domains/engine/ -v
```
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/engine/__init__.py tests/domains/engine/test_engine_run.py
git commit -m "feat: add engine domain run() orchestrator entry point"
```

---

### Task 18: Update utils.py shim + delete old stubs

**Files:**
- Modify: `pipeline/utils.py`
- Delete: `pipeline/extract_classes.py`, `pipeline/extract_economy.py`, `pipeline/extract_engine.py`, `pipeline/extract_gameplay.py`, `pipeline/extract_items.py`, `pipeline/extract_maps.py`, `pipeline/extract_monsters.py`, `pipeline/extract_enums.py` (superseded by `domains/engine/extract_enums.py` — see Task 13 note)

- [ ] **Step 1: Update utils.py to re-export core/ helpers**

Replace `pipeline/utils.py` content with a thin shim:

```python
"""
Backwards-compatible shim. New code should import from pipeline.core directly.
This module re-exports core/ helpers for scripts that still reference utils.py.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from pipeline.core.reader import load, find_files
from pipeline.core.normalizer import flatten, camel_to_snake
from pipeline.core.writer import Writer as _Writer

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "raw"
EXTRACTED_DIR = REPO_ROOT / "extracted"


def read_raw(relative_path: str) -> dict:
    """Read a JSON file from raw/ and return parsed data."""
    path = RAW_DIR / relative_path
    if not path.exists():
        raise FileNotFoundError(f"Raw file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_raw_files(pattern: str) -> list[Path]:
    """Glob for files in raw/ matching a pattern."""
    return sorted(RAW_DIR.glob(pattern))


def slugify(name: str) -> str:
    return name.lower().strip().replace(" ", "_").replace("-", "_")


def write_extracted(domain: str, filename: str, data: dict, source_path: str = ""):
    """Legacy writer — new code should use pipeline.core.writer.Writer."""
    writer = _Writer(EXTRACTED_DIR, pipeline_version="0.1.0")
    writer.write_entity(domain, filename, data, source_files=[source_path] if source_path else [])


def write_extracted_index(domain: str, entries: list[dict]):
    """Legacy index writer."""
    writer = _Writer(EXTRACTED_DIR, pipeline_version="0.1.0")
    writer.write_index(domain, entries)


def flatten_uasset(value):
    """Legacy name — delegates to pipeline.core.normalizer.flatten."""
    return flatten(value)


def snake_case(name: str) -> str:
    """Legacy name — delegates to pipeline.core.normalizer.camel_to_snake."""
    return camel_to_snake(name)
```

- [ ] **Step 2: Delete old domain stubs (including standalone extract_enums.py)**

```bash
cd darkanddarker-wiki/pipeline && rm extract_classes.py extract_economy.py extract_engine.py extract_gameplay.py extract_items.py extract_maps.py extract_monsters.py extract_enums.py
```

- [ ] **Step 3: Verify all tests still pass after deletion**

```bash
cd darkanddarker-wiki && py -3 -m pytest tests/ -v --tb=short 2>&1 | tail -20
```
Expected: all tests still PASS (no tests depended on the deleted stubs)

- [ ] **Step 4: Commit**

```bash
git add pipeline/utils.py
git rm pipeline/extract_classes.py pipeline/extract_economy.py pipeline/extract_engine.py pipeline/extract_gameplay.py pipeline/extract_items.py pipeline/extract_maps.py pipeline/extract_monsters.py pipeline/extract_enums.py
git commit -m "refactor: update utils.py shim, delete replaced domain stubs including extract_enums.py"
```

---

### Task 19: Integration test — run engine domain on real data

- [ ] **Step 1: Run the engine domain against real raw/ data**

```bash
cd darkanddarker-wiki && py -3 -c "
from pathlib import Path
from pipeline.domains.engine import run

raw = Path('raw')
extracted = Path('extracted')
summary = run(raw_root=raw, extracted_root=extracted)
print('Summary:', summary)
assert summary['enums'] > 0, 'Expected at least one enum extracted'
assert summary['constants'] > 0, 'Expected at least one constant extracted'
print('Assertions passed.')
"
```
Expected: prints extraction counts with `enums > 0` and `constants > 0`, no AssertionError

- [ ] **Step 2: Verify output files exist and have non-empty data**

```bash
py -3 -c "
import json
from pathlib import Path

enums = json.loads(Path('extracted/engine/enums.json').read_text(encoding='utf-8'))
# _meta key is present and all other keys are enum names
enum_names = [k for k in enums if not k.startswith('_')]
assert len(enum_names) > 0, f'enums.json has no enum entries, keys={list(enums.keys())}'
print(f'enums.json: {len(enum_names)} enums')

curves = json.loads(Path('extracted/engine/curves.json').read_text(encoding='utf-8'))
assert 'curve_tables' in curves, 'curves.json missing curve_tables key'
print(f'curves.json: {len(curves[\"curve_tables\"])} curve tables, {len(curves.get(\"curve_floats\", {}))} curve floats')

print('All output file assertions passed.')
"
```
Expected: prints counts with no AssertionError

- [ ] **Step 3: Verify enums.json has correct _meta format**

```bash
py -3 -c "
import json
from pathlib import Path
data = json.loads(Path('extracted/engine/enums.json').read_text(encoding='utf-8'))
meta = data.get('_meta', {})
assert isinstance(meta.get('source_files'), list), '_meta.source_files must be a list'
assert meta.get('pipeline_version') == '1.0.0', f'Expected 1.0.0, got {meta.get(\"pipeline_version\")}'
assert 'extracted_at' in meta, '_meta.extracted_at missing'
print('_meta format: OK')
print('pipeline_version:', meta['pipeline_version'])
print('source_files count:', len(meta['source_files']))
"
```
Expected: prints `_meta format: OK` with no AssertionError

- [ ] **Step 4: Commit updated extracted outputs**

```bash
git add extracted/engine/
git commit -m "data: regenerate engine extracted files with v1.0.0 pipeline"
```

---

## Final: Run all tests

- [ ] **Step 1: Run complete test suite**

```bash
cd darkanddarker-wiki && py -3 -m pytest tests/ -v
```
Expected: all tests PASS with no errors or warnings

- [ ] **Step 2: Verify directory structure matches spec §2.1**

```bash
find darkanddarker-wiki/pipeline -type f -name "*.py" | sort
```
Expected output includes:
```
pipeline/core/__init__.py
pipeline/core/analyzer.py
pipeline/core/normalizer.py
pipeline/core/reader.py
pipeline/core/resolver.py
pipeline/core/writer.py
pipeline/domains/__init__.py
pipeline/domains/engine/__init__.py
pipeline/domains/engine/extract_constants.py
pipeline/domains/engine/extract_curves.py
pipeline/domains/engine/extract_enums.py
pipeline/domains/engine/extract_tags.py
pipeline/extract_all.py
pipeline/utils.py
```
Note: `pipeline/extract_enums.py` is absent — it was deleted in Task 18 and superseded by `domains/engine/extract_enums.py`.

- [ ] **Step 3: Final commit tag**

```bash
git add -A
git commit -m "feat: complete Phase 1 — core library + engine domain extractor"
```
