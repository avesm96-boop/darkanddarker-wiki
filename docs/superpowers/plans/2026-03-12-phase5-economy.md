# Phase 5: Economy Domain Extractor Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `pipeline/domains/economy/` with 4 sub-extractors (merchants, marketplaces, parcels, workshops) producing `extracted/economy/<id>.json` entity files and a combined `_index.json`.

**Architecture:** Each sub-extractor is a focused module with one `extract_*()` function and one `run_*()` function. `__init__.py` orchestrates all four sub-extractors and writes a single combined index, following the exact pattern of `pipeline/domains/spawns/__init__.py` (dispatch table pattern). Each extractor that resolves asset refs defines a local `_extract_asset_id()` helper (same pattern as `extract_aoes.py`). Workshop files have no Properties at all — `extract_workshop()` must not return `None` when Properties is absent; it produces `{"id": obj["Name"]}`.

**Tech Stack:** Python 3.10+, pytest, pathlib, pipeline.core (reader, writer, normalizer)

---

## Chunk 1: Test Infrastructure + Merchants + Marketplaces

### File Map

- Create: `pipeline/domains/economy/__init__.py` (empty stub)
- Create: `pipeline/domains/economy/extract_merchants.py`
- Create: `pipeline/domains/economy/extract_marketplaces.py`
- Create: `tests/domains/economy/__init__.py` (empty)
- Create: `tests/domains/economy/test_extract_merchants.py`
- Create: `tests/domains/economy/test_extract_marketplaces.py`

---

### Task 1: Test infrastructure

**Files:**
- Create: `pipeline/domains/economy/__init__.py` (empty stub)
- Create: `tests/domains/economy/__init__.py` (empty)

- [ ] **Step 1: Create the two empty `__init__.py` files**

`pipeline/domains/economy/__init__.py`:
```python
"""Economy domain extractor — run() called by extract_all.py orchestrator."""
```

`tests/domains/economy/__init__.py`:
```python
```
(empty file)

- [ ] **Step 2: Verify pytest can collect from the new directory**

Run from `darkanddarker-wiki/`:
```bash
py -3 -m pytest tests/domains/economy/ --collect-only
```
Expected: `no tests ran`

---

### Task 2: extract_merchants.py — DCBaseGearDataAsset

**Files:**
- Create: `pipeline/domains/economy/extract_merchants.py`
- Create: `tests/domains/economy/test_extract_merchants.py`

- [ ] **Step 1: Write the failing tests**

`tests/domains/economy/test_extract_merchants.py`:
```python
"""Tests for pipeline/domains/economy/extract_merchants.py"""
import json
from pathlib import Path
from pipeline.domains.economy.extract_merchants import extract_merchant, run_merchants


def make_merchant_file(tmp_path, merchant_id):
    data = [{
        "Type": "DCBaseGearDataAsset",
        "Name": merchant_id,
        "Properties": {
            "BaseGearItemArray": [
                {
                    "UniqueID": 2,
                    "ItemId": {
                        "AssetPathName": "/Game/.../Id_Item_ArmingSword_1001.Id_Item_ArmingSword_1001",
                        "SubPathString": "",
                    },
                    "MerchantId": {
                        "AssetPathName": "/Game/.../Id_Merchant_Weaponsmith.Id_Merchant_Weaponsmith",
                        "SubPathString": "",
                    },
                    "RequiredAffinity": 0,
                }
            ]
        },
    }]
    f = tmp_path / f"{merchant_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_merchant_returns_id_and_items(tmp_path):
    f = make_merchant_file(tmp_path, "Id_BaseGear_Squire_Test")
    result = extract_merchant(f)
    assert result is not None
    assert result["id"] == "Id_BaseGear_Squire_Test"
    assert isinstance(result["items"], list)
    assert len(result["items"]) == 1
    item = result["items"][0]
    assert item["unique_id"] == 2
    assert item["item_id"] == "Id_Item_ArmingSword_1001"
    assert item["merchant_id"] == "Id_Merchant_Weaponsmith"
    assert item["required_affinity"] == 0


def test_extract_merchant_handles_empty_items(tmp_path):
    data = [{
        "Type": "DCBaseGearDataAsset",
        "Name": "Id_BaseGear_Empty",
        "Properties": {"BaseGearItemArray": []},
    }]
    f = tmp_path / "empty.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    result = extract_merchant(f)
    assert result is not None
    assert result["items"] == []


def test_extract_merchant_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_merchant(f) is None


def test_run_merchants_writes_entity_and_index(tmp_path):
    merchant_dir = tmp_path / "merchants"
    merchant_dir.mkdir()
    make_merchant_file(merchant_dir, "Id_BaseGear_Squire_Test")
    extracted = tmp_path / "extracted"
    result = run_merchants(merchant_dir=merchant_dir, extracted_root=extracted)
    entity = extracted / "economy" / "Id_BaseGear_Squire_Test.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id"] == "Id_BaseGear_Squire_Test"
    assert isinstance(data["items"], list)
    assert "_meta" in data
    index = extracted / "economy" / "_index.json"
    assert index.exists()
    assert "Id_BaseGear_Squire_Test" in result
```

- [ ] **Step 2: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/economy/test_extract_merchants.py -v
```
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `pipeline/domains/economy/extract_merchants.py`**

`pipeline/domains/economy/extract_merchants.py`:
```python
"""Extract DCBaseGearDataAsset files → extracted/economy/<id>.json + _index.json."""
import logging
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.writer import Writer

logger = logging.getLogger(__name__)


def _extract_asset_id(ref: dict) -> str | None:
    """Extract asset ID from {"AssetPathName": "/Game/.../Foo.Foo", "SubPathString": ""}."""
    if not isinstance(ref, dict):
        return None
    asset_path = ref.get("AssetPathName", "")
    if not asset_path:
        return None
    parts = asset_path.split(".")
    return parts[-1] if len(parts) > 1 else None


def extract_merchant(file_path: Path) -> dict | None:
    """Extract one DCBaseGearDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        logger.error("Failed to load merchant file: %s", e)
        return None

    obj = next(
        (o for o in data if isinstance(o, dict) and o.get("Type") == "DCBaseGearDataAsset"),
        None,
    )
    if not obj:
        return None

    props = get_properties(obj)
    items = [
        {
            "unique_id": item.get("UniqueID"),
            "item_id": _extract_asset_id(item.get("ItemId")),
            "merchant_id": _extract_asset_id(item.get("MerchantId")),
            "required_affinity": item.get("RequiredAffinity"),
        }
        for item in (props.get("BaseGearItemArray") or [])
    ]

    return {
        "id": obj["Name"],
        "items": items,
    }


def run_merchants(merchant_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCBaseGearDataAsset files."""
    files = find_files(str(Path(merchant_dir) / "*.json"))
    print(f"  [merchants] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    merchants = {}

    for f in files:
        result = extract_merchant(f)
        if not result:
            continue
        merchant_id = result["id"]
        merchants[merchant_id] = result
        writer.write_entity("economy", merchant_id, result, source_files=[str(f)])
        index_entries.append({"id": merchant_id})

    writer.write_index("economy", index_entries)
    print(f"  [merchants] Extracted {len(merchants)} merchants")
    return merchants
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/economy/test_extract_merchants.py -v
```
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/economy/__init__.py pipeline/domains/economy/extract_merchants.py tests/domains/economy/__init__.py tests/domains/economy/test_extract_merchants.py
git commit -m "feat: add economy domain + extract_merchants extractor"
```

---

### Task 3: extract_marketplaces.py — DCMarketplaceDataAsset

**Files:**
- Create: `pipeline/domains/economy/extract_marketplaces.py`
- Create: `tests/domains/economy/test_extract_marketplaces.py`

- [ ] **Step 1: Write the failing tests**

`tests/domains/economy/test_extract_marketplaces.py`:
```python
"""Tests for pipeline/domains/economy/extract_marketplaces.py"""
import json
from pathlib import Path
from pipeline.domains.economy.extract_marketplaces import extract_marketplace, run_marketplaces


def make_marketplace_file(tmp_path, marketplace_id):
    data = [{
        "Type": "DCMarketplaceDataAsset",
        "Name": marketplace_id,
        "Properties": {
            "Name": {"Namespace": "DC", "Key": "some_key", "LocalizedString": "Marketplace"},
            "Order": 1,
            "BasePayments": [
                {
                    "AssetPathName": "/Game/.../Id_MarketplacePayment_GoldCoin.Id_MarketplacePayment_GoldCoin",
                    "SubPathString": "",
                }
            ],
        },
    }]
    f = tmp_path / f"{marketplace_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_marketplace_returns_id_and_fields(tmp_path):
    f = make_marketplace_file(tmp_path, "Id_Marketplace_GoldCoin")
    result = extract_marketplace(f)
    assert result is not None
    assert result["id"] == "Id_Marketplace_GoldCoin"
    assert result["name"] == "Marketplace"
    assert result["order"] == 1
    assert isinstance(result["base_payments"], list)
    assert len(result["base_payments"]) == 1
    assert result["base_payments"][0] == "Id_MarketplacePayment_GoldCoin"


def test_extract_marketplace_handles_empty_payments(tmp_path):
    data = [{
        "Type": "DCMarketplaceDataAsset",
        "Name": "Id_Marketplace_Empty",
        "Properties": {
            "Name": {"LocalizedString": "Empty Market"},
            "Order": 0,
            "BasePayments": [],
        },
    }]
    f = tmp_path / "empty.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    result = extract_marketplace(f)
    assert result is not None
    assert result["base_payments"] == []


def test_extract_marketplace_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_marketplace(f) is None


def test_run_marketplaces_writes_entity_and_index(tmp_path):
    marketplace_dir = tmp_path / "marketplaces"
    marketplace_dir.mkdir()
    make_marketplace_file(marketplace_dir, "Id_Marketplace_GoldCoin")
    extracted = tmp_path / "extracted"
    result = run_marketplaces(marketplace_dir=marketplace_dir, extracted_root=extracted)
    entity = extracted / "economy" / "Id_Marketplace_GoldCoin.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id"] == "Id_Marketplace_GoldCoin"
    assert data["name"] == "Marketplace"
    assert "_meta" in data
    index = extracted / "economy" / "_index.json"
    assert index.exists()
    assert "Id_Marketplace_GoldCoin" in result
```

- [ ] **Step 2: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/economy/test_extract_marketplaces.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement `pipeline/domains/economy/extract_marketplaces.py`**

`pipeline/domains/economy/extract_marketplaces.py`:
```python
"""Extract DCMarketplaceDataAsset files → extracted/economy/<id>.json + _index.json."""
import logging
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_text
from pipeline.core.writer import Writer

logger = logging.getLogger(__name__)


def _extract_asset_id(ref: dict) -> str | None:
    """Extract asset ID from {"AssetPathName": "/Game/.../Foo.Foo", "SubPathString": ""}."""
    if not isinstance(ref, dict):
        return None
    asset_path = ref.get("AssetPathName", "")
    if not asset_path:
        return None
    parts = asset_path.split(".")
    return parts[-1] if len(parts) > 1 else None


def extract_marketplace(file_path: Path) -> dict | None:
    """Extract one DCMarketplaceDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        logger.error("Failed to load marketplace file: %s", e)
        return None

    obj = next(
        (o for o in data if isinstance(o, dict) and o.get("Type") == "DCMarketplaceDataAsset"),
        None,
    )
    if not obj:
        return None

    props = get_properties(obj)
    base_payments = [
        _extract_asset_id(ref)
        for ref in (props.get("BasePayments") or [])
        if _extract_asset_id(ref) is not None
    ]

    return {
        "id": obj["Name"],
        "name": resolve_text(props.get("Name")),
        "order": props.get("Order"),
        "base_payments": base_payments,
    }


def run_marketplaces(marketplace_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCMarketplaceDataAsset files."""
    files = find_files(str(Path(marketplace_dir) / "*.json"))
    print(f"  [marketplaces] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    marketplaces = {}

    for f in files:
        result = extract_marketplace(f)
        if not result:
            continue
        marketplace_id = result["id"]
        marketplaces[marketplace_id] = result
        writer.write_entity("economy", marketplace_id, result, source_files=[str(f)])
        index_entries.append({"id": marketplace_id})

    writer.write_index("economy", index_entries)
    print(f"  [marketplaces] Extracted {len(marketplaces)} marketplaces")
    return marketplaces
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/economy/test_extract_marketplaces.py -v
```
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/economy/extract_marketplaces.py tests/domains/economy/test_extract_marketplaces.py
git commit -m "feat: add extract_marketplaces extractor"
```

---

## Chunk 2: Parcels + Workshops + Orchestrator + Integration Test

### File Map

- Create: `pipeline/domains/economy/extract_parcels.py`
- Create: `pipeline/domains/economy/extract_workshops.py`
- Modify: `pipeline/domains/economy/__init__.py` (full orchestrator)
- Create: `tests/domains/economy/test_extract_parcels.py`
- Create: `tests/domains/economy/test_extract_workshops.py`
- Create: `tests/domains/economy/test_economy_integration.py`

---

### Task 4: extract_parcels.py — DCParcelDataAsset

**Files:**
- Create: `pipeline/domains/economy/extract_parcels.py`
- Create: `tests/domains/economy/test_extract_parcels.py`

- [ ] **Step 1: Write the failing tests**

`tests/domains/economy/test_extract_parcels.py`:
```python
"""Tests for pipeline/domains/economy/extract_parcels.py"""
import json
from pathlib import Path
from pipeline.domains.economy.extract_parcels import extract_parcel, run_parcels


def make_parcel_file(tmp_path, parcel_id):
    data = [{
        "Type": "DCParcelDataAsset",
        "Name": parcel_id,
        "Properties": {
            "Name": {"LocalizedString": "Recovered Seasonal Pack Gold Coin Bag"},
            "FlavorText": {"LocalizedString": "A Parcel ready to be collected from the Expressman."},
            "ArtData": {
                "AssetPathName": "/Game/.../Reward_Parcel_CoinBagRestore_01.Reward_Parcel_CoinBagRestore_01",
                "SubPathString": "",
            },
            "ParcelRewards": [
                {
                    "AssetPathName": "/Game/.../Id_Reward_Parcel_Restore_Bag_01.Id_Reward_Parcel_Restore_Bag_01",
                    "SubPathString": "",
                }
            ],
        },
    }]
    f = tmp_path / f"{parcel_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_parcel_returns_id_and_fields(tmp_path):
    f = make_parcel_file(tmp_path, "Id_Parcel_CoinBag_Restore_01")
    result = extract_parcel(f)
    assert result is not None
    assert result["id"] == "Id_Parcel_CoinBag_Restore_01"
    assert result["name"] == "Recovered Seasonal Pack Gold Coin Bag"
    assert result["flavor_text"] == "A Parcel ready to be collected from the Expressman."
    assert isinstance(result["parcel_rewards"], list)
    assert len(result["parcel_rewards"]) == 1
    assert result["parcel_rewards"][0] == "Id_Reward_Parcel_Restore_Bag_01"


def test_extract_parcel_handles_empty_rewards(tmp_path):
    data = [{
        "Type": "DCParcelDataAsset",
        "Name": "Id_Parcel_Empty",
        "Properties": {
            "Name": {"LocalizedString": "Empty Parcel"},
            "FlavorText": {"LocalizedString": "Nothing here."},
            "ParcelRewards": [],
        },
    }]
    f = tmp_path / "empty.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    result = extract_parcel(f)
    assert result is not None
    assert result["parcel_rewards"] == []


def test_extract_parcel_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_parcel(f) is None


def test_run_parcels_writes_entity_and_index(tmp_path):
    parcel_dir = tmp_path / "parcels"
    parcel_dir.mkdir()
    make_parcel_file(parcel_dir, "Id_Parcel_CoinBag_Restore_01")
    extracted = tmp_path / "extracted"
    result = run_parcels(parcel_dir=parcel_dir, extracted_root=extracted)
    entity = extracted / "economy" / "Id_Parcel_CoinBag_Restore_01.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id"] == "Id_Parcel_CoinBag_Restore_01"
    assert data["name"] == "Recovered Seasonal Pack Gold Coin Bag"
    assert "_meta" in data
    index = extracted / "economy" / "_index.json"
    assert index.exists()
    assert "Id_Parcel_CoinBag_Restore_01" in result
```

- [ ] **Step 2: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/economy/test_extract_parcels.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement `pipeline/domains/economy/extract_parcels.py`**

`pipeline/domains/economy/extract_parcels.py`:
```python
"""Extract DCParcelDataAsset files → extracted/economy/<id>.json + _index.json."""
import logging
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_text
from pipeline.core.writer import Writer

logger = logging.getLogger(__name__)


def _extract_asset_id(ref: dict) -> str | None:
    """Extract asset ID from {"AssetPathName": "/Game/.../Foo.Foo", "SubPathString": ""}."""
    if not isinstance(ref, dict):
        return None
    asset_path = ref.get("AssetPathName", "")
    if not asset_path:
        return None
    parts = asset_path.split(".")
    return parts[-1] if len(parts) > 1 else None


def extract_parcel(file_path: Path) -> dict | None:
    """Extract one DCParcelDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        logger.error("Failed to load parcel file: %s", e)
        return None

    obj = next(
        (o for o in data if isinstance(o, dict) and o.get("Type") == "DCParcelDataAsset"),
        None,
    )
    if not obj:
        return None

    props = get_properties(obj)
    parcel_rewards = [
        _extract_asset_id(ref)
        for ref in (props.get("ParcelRewards") or [])
        if _extract_asset_id(ref) is not None
    ]

    return {
        "id": obj["Name"],
        "name": resolve_text(props.get("Name")),
        "flavor_text": resolve_text(props.get("FlavorText")),
        "parcel_rewards": parcel_rewards,
    }


def run_parcels(parcel_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCParcelDataAsset files."""
    files = find_files(str(Path(parcel_dir) / "*.json"))
    print(f"  [parcels] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    parcels = {}

    for f in files:
        result = extract_parcel(f)
        if not result:
            continue
        parcel_id = result["id"]
        parcels[parcel_id] = result
        writer.write_entity("economy", parcel_id, result, source_files=[str(f)])
        index_entries.append({"id": parcel_id})

    writer.write_index("economy", index_entries)
    print(f"  [parcels] Extracted {len(parcels)} parcels")
    return parcels
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/economy/test_extract_parcels.py -v
```
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/economy/extract_parcels.py tests/domains/economy/test_extract_parcels.py
git commit -m "feat: add extract_parcels extractor"
```

---

### Task 5: extract_workshops.py — DCWorkshopDataAsset

**Files:**
- Create: `pipeline/domains/economy/extract_workshops.py`
- Create: `tests/domains/economy/test_extract_workshops.py`

**Important:** All workshop files in the raw data have NO `Properties` key — only `Type` and `Name`. The extractor must produce `{"id": obj["Name"]}` and must NOT return `None` for a valid `DCWorkshopDataAsset` object even when Properties is absent. `run_workshops` uses glob `"*.json"` since all files in the directory are valid. `get_properties` is not needed.

- [ ] **Step 1: Write the failing tests**

`tests/domains/economy/test_extract_workshops.py`:
```python
"""Tests for pipeline/domains/economy/extract_workshops.py"""
import json
from pathlib import Path
from pipeline.domains.economy.extract_workshops import extract_workshop, run_workshops


def make_workshop_file(tmp_path, workshop_id, include_properties=False):
    data = [{"Type": "DCWorkshopDataAsset", "Name": workshop_id}]
    if include_properties:
        data[0]["Properties"] = {}
    f = tmp_path / f"{workshop_id}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_extract_workshop_returns_id_without_properties(tmp_path):
    f = make_workshop_file(tmp_path, "Id_Workshop_Blacksmith")
    result = extract_workshop(f)
    assert result is not None
    assert result["id"] == "Id_Workshop_Blacksmith"


def test_extract_workshop_returns_id_with_empty_properties(tmp_path):
    f = make_workshop_file(tmp_path, "Id_Workshop_Alchemist", include_properties=True)
    result = extract_workshop(f)
    assert result is not None
    assert result["id"] == "Id_Workshop_Alchemist"


def test_extract_workshop_returns_none_for_wrong_type(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('[{"Type": "DCOtherDataAsset"}]', encoding="utf-8")
    assert extract_workshop(f) is None


def test_run_workshops_writes_entity_and_index(tmp_path):
    workshop_dir = tmp_path / "workshops"
    workshop_dir.mkdir()
    make_workshop_file(workshop_dir, "Id_Workshop_Blacksmith")
    extracted = tmp_path / "extracted"
    result = run_workshops(workshop_dir=workshop_dir, extracted_root=extracted)
    entity = extracted / "economy" / "Id_Workshop_Blacksmith.json"
    assert entity.exists()
    data = json.loads(entity.read_text(encoding="utf-8"))
    assert data["id"] == "Id_Workshop_Blacksmith"
    assert "_meta" in data
    index = extracted / "economy" / "_index.json"
    assert index.exists()
    assert "Id_Workshop_Blacksmith" in result
```

- [ ] **Step 2: Run to verify tests fail**

```bash
py -3 -m pytest tests/domains/economy/test_extract_workshops.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement `pipeline/domains/economy/extract_workshops.py`**

`pipeline/domains/economy/extract_workshops.py`:
```python
"""Extract DCWorkshopDataAsset files → extracted/economy/<id>.json + _index.json.

NOTE: All workshop files in the raw data have no Properties — only Type and Name.
extract_workshop() produces {"id": obj["Name"]} and never returns None for a valid
DCWorkshopDataAsset object.
"""
import logging
from pathlib import Path

from pipeline.core.reader import load, find_files
from pipeline.core.writer import Writer

logger = logging.getLogger(__name__)


def extract_workshop(file_path: Path) -> dict | None:
    """Extract one DCWorkshopDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        logger.error("Failed to load workshop file: %s", e)
        return None

    obj = next(
        (o for o in data if isinstance(o, dict) and o.get("Type") == "DCWorkshopDataAsset"),
        None,
    )
    if not obj:
        return None

    return {"id": obj["Name"]}


def run_workshops(workshop_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCWorkshopDataAsset files."""
    files = find_files(str(Path(workshop_dir) / "*.json"))
    print(f"  [workshops] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    workshops = {}

    for f in files:
        result = extract_workshop(f)
        if not result:
            continue
        workshop_id = result["id"]
        workshops[workshop_id] = result
        writer.write_entity("economy", workshop_id, result, source_files=[str(f)])
        index_entries.append({"id": workshop_id})

    writer.write_index("economy", index_entries)
    print(f"  [workshops] Extracted {len(workshops)} workshops")
    return workshops
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
py -3 -m pytest tests/domains/economy/test_extract_workshops.py -v
```
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add pipeline/domains/economy/extract_workshops.py tests/domains/economy/test_extract_workshops.py
git commit -m "feat: add extract_workshops extractor"
```

---

### Task 6: economy/__init__.py — orchestrator

**Files:**
- Modify: `pipeline/domains/economy/__init__.py`

- [ ] **Step 1: Replace the stub with the full orchestrator**

`pipeline/domains/economy/__init__.py`:
```python
"""Economy domain extractor — run() called by extract_all.py orchestrator."""
from pathlib import Path

from pipeline.domains.economy.extract_merchants import run_merchants
from pipeline.domains.economy.extract_marketplaces import run_marketplaces
from pipeline.domains.economy.extract_parcels import run_parcels
from pipeline.domains.economy.extract_workshops import run_workshops
from pipeline.core.writer import Writer

_V2_BASE = "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2"


def run(raw_root: Path, extracted_root: Path) -> dict:
    """Run all economy domain extractors. Returns summary of counts.

    NOTE: Individual run_* functions each write a partial _index.json as a
    side-effect (useful for standalone runs / unit tests). This orchestrator
    overwrites that partial index with a single combined index containing all
    entity types at the end.
    """
    print("[economy] Starting extraction...")
    summary = {}
    all_entities: dict[str, dict] = {}

    dirs = {
        "merchant":    raw_root / _V2_BASE / "Merchant" / "BaseGear",
        "marketplace": raw_root / _V2_BASE / "Marketplace" / "Marketplace",
        "parcel":      raw_root / _V2_BASE / "Parcel" / "Parcel",
        "workshop":    raw_root / _V2_BASE / "Workshop" / "Workshop",
    }

    for key, fn, dir_key, entity_type, param in [
        ("merchants",    run_merchants,    "merchant",    "merchant",    "merchant_dir"),
        ("marketplaces", run_marketplaces, "marketplace", "marketplace", "marketplace_dir"),
        ("parcels",      run_parcels,      "parcel",      "parcel",      "parcel_dir"),
        ("workshops",    run_workshops,    "workshop",    "workshop",    "workshop_dir"),
    ]:
        d = dirs[dir_key]
        if d.exists():
            entities = fn(**{param: d, "extracted_root": extracted_root})
            summary[key] = len(entities)
            all_entities.update({k: {**v, "_entity_type": entity_type}
                                  for k, v in entities.items()})
        else:
            print(f"  [economy] WARNING: {d} not found")
            summary[key] = 0

    # Write combined index (overwrites partial indexes from individual run_* calls)
    combined_index = [
        {"id": v["id"], "type": v["_entity_type"]}
        for v in all_entities.values()
    ]
    Writer(extracted_root).write_index("economy", combined_index)

    print(f"[economy] Done. Summary: {summary}")
    return summary
```

- [ ] **Step 2: Run full economy test suite (excluding integration) to verify nothing broke**

```bash
py -3 -m pytest tests/domains/economy/ -v --ignore=tests/domains/economy/test_economy_integration.py
```
Expected: All PASSED

- [ ] **Step 3: Commit**

```bash
git add pipeline/domains/economy/__init__.py
git commit -m "feat: complete economy orchestrator in __init__.py"
```

---

### Task 7: Integration test + full suite verification

**Files:**
- Create: `tests/domains/economy/test_economy_integration.py`

- [ ] **Step 1: Create the integration test**

`tests/domains/economy/test_economy_integration.py`:
```python
"""Integration test: run economy domain against real raw data."""
import json
from pathlib import Path
import pytest
from pipeline.domains.economy import run

RAW_ROOT = Path("raw")
MERCHANT_DIR = RAW_ROOT / "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/Merchant/BaseGear"


@pytest.mark.skipif(not MERCHANT_DIR.exists(), reason="raw data not present")
def test_economy_run_integration(tmp_path):
    summary = run(raw_root=RAW_ROOT, extracted_root=tmp_path)
    assert summary.get("merchants", 0) > 100
    assert summary.get("marketplaces", 0) > 0
    assert summary.get("parcels", 0) > 20
    assert summary.get("workshops", 0) > 10
    index = tmp_path / "economy" / "_index.json"
    assert index.exists()
    index_data = json.loads(index.read_text(encoding="utf-8"))
    entity_types = {e["type"] for e in index_data["entries"]}
    assert "merchant" in entity_types
    assert "marketplace" in entity_types
    assert "parcel" in entity_types
    assert "workshop" in entity_types
```

- [ ] **Step 2: Run full test suite to verify all tests pass**

```bash
py -3 -m pytest tests/ -v --tb=short 2>&1 | tail -20
```
Expected: All prior tests + all new economy tests PASSED (integration test skipped if no raw data)

- [ ] **Step 3: Commit**

```bash
git add tests/domains/economy/test_economy_integration.py
git commit -m "test: add economy integration test"
```

---

## Final verification

- [ ] **Run the complete test suite one final time**

```bash
py -3 -m pytest tests/ --tb=short 2>&1 | tail -5
```
Expected: All tests passed, 0 failures
