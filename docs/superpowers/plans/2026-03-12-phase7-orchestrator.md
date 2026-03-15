# Phase 7: extract_all.py Orchestrator Rewrite Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite `pipeline/extract_all.py` as a phase-based orchestrator that imports and calls all 11 domain `run()` functions in dependency order, with parallel execution within phases, manifest-based skip logic, `--domain` and `--force` CLI flags, resolver hydration between phases, failure propagation to downstream phases, and a run summary table.

**Architecture:** A single `pipeline/extract_all.py` module that uses `importlib` for dynamic domain imports, `concurrent.futures.ThreadPoolExecutor` for intra-phase parallelism, `argparse` for CLI flags, and `mtime` comparison of `extracted/<domain>/_index.json` vs the newest file in the domain's raw source dirs for skip logic. The resolver is hydrated from the main thread after each domain completes successfully, never from worker threads.

**Tech Stack:** Python 3.10+, `concurrent.futures`, `argparse`, `importlib`, `pathlib`, `pytest`, `unittest.mock`

**Spec:** `docs/superpowers/specs/2026-03-12-full-extraction-pipeline-design.md` §6

---

## Chunk 1: Implement `pipeline/extract_all.py`

### File Map

- Rewrite: `pipeline/extract_all.py`

---

### Task 1: Implement `extract_all.py`

**Files:**
- Rewrite: `pipeline/extract_all.py`

- [ ] **Step 1: Write `pipeline/extract_all.py`**

Replace the entire contents of `pipeline/extract_all.py` with:

```python
"""Phase-based orchestrator for the Dark and Darker wiki extraction pipeline.

Domains within each phase run concurrently via ThreadPoolExecutor.
Resolver hydration (load_domain) is called from the main thread after each
domain completes — never from worker threads (see core/resolver.py thread
safety contract).

Usage:
    py -3 -m pipeline.extract_all                # run all, skip up-to-date domains
    py -3 -m pipeline.extract_all --force        # re-run everything
    py -3 -m pipeline.extract_all --domain items # re-run items + all downstream phases
"""

from __future__ import annotations

import argparse
import importlib
import sys
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

from pipeline.core.resolver import Resolver

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

RAW_ROOT = Path(__file__).resolve().parent.parent / "raw"
EXTRACTED_ROOT = Path(__file__).resolve().parent.parent / "extracted"

# V2 base path used for raw source file discovery (mtime checks).
_V2_BASE = "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2"

# ---------------------------------------------------------------------------
# Phase definition
# Domains within the same phase run in parallel.
# Phases run sequentially; a phase failure blocks all downstream phases.
# cosmetics is not yet implemented — excluded from PHASES.
# ---------------------------------------------------------------------------

PHASES: list[list[str]] = [
    ["engine"],
    ["items", "classes", "monsters"],
    ["combat", "spells", "status"],
    ["dungeons", "spawns"],
    ["economy"],
    ["quests"],
]

# Flat ordered list, used for downstream-phase calculation.
_ALL_DOMAINS: list[str] = [d for phase in PHASES for d in phase]

# ---------------------------------------------------------------------------
# Raw source directories per domain
# Used by should_skip_domain() to find the newest raw file mtime.
# Each entry is a list of V2 sub-paths to glob for *.json files.
# ---------------------------------------------------------------------------

_DOMAIN_RAW_SUBDIRS: dict[str, list[str]] = {
    "engine": [
        "Constant/Constant",
        "IdTagGroup/IdTagGroup",
        "AbilityRelationshipTagGroup/AbilityRelationshipTagGroup",
        "GameplayCueTagGroup/GameplayCueTagGroup",
        "GameplayEffectRelationTagGroup/GameplayEffectRelationTagGroup",
        "TagMessageRelationshipTagGroup/TagMessageRelationshipTagGroup",
        "InteractSettingGroup/InteractSettingGroup",
    ],
    "items": [
        "Item/Item",
        "ItemProperty/ItemProperty",
        "ItemProperty/ItemPropertyType",
    ],
    "classes": [
        "PlayerCharacter/PlayerCharacter",
        "Perk/Perk",
        "Skill/Skill",
        "ShapeShift/ShapeShift",
    ],
    "monsters": [
        "Monster/Monster",
    ],
    "combat": [
        "MeleeAttack/MeleeAttack",
        "Projectile/Projectile",
        "Aoe/Aoe",
        "MovementModifier/MovementModifier",
        "GEModifier/GEModifier",
    ],
    "spells": [
        "Spell/Spell",
        "Religion/Religion",
        "FaustianBargain/FaustianBargain",
    ],
    "status": [
        "ActorStatus/ActorStatus",
        "ActorStatusInWater/ActorStatusInWater",
        "ActorStatusItemCosmetic/ActorStatusItemCosmetic",
        "ActorStatusMonster/ActorStatusMonster",
    ],
    "dungeons": [
        "Dungeon/Dungeon",
        "FloorRule",           # non-standard layout; glob entire directory
        "Props/Props",
        "MapIcon/MapIcon",
        "Vehicle/Vehicle",
    ],
    "spawns": [
        "Spawner/Spawner",
        "LootDrop/LootDrop",
    ],
    "economy": [
        "Merchant/Merchant",
        "Shop",                # non-standard layout; glob entire directory
        "Marketplace/Marketplace",
        "Parcel/Parcel",
        "Workshop/Workshop",
    ],
    "quests": [
        "Quest/Quest",
        "Achievement/Achievement",
        "TriumphLevel/TriumphLevel",
        "Leaderboard/Leaderboard",
        "Announce/Announce",
    ],
}


# ---------------------------------------------------------------------------
# Skip logic
# ---------------------------------------------------------------------------

def _newest_raw_mtime(domain: str, raw_root: Path) -> float | None:
    """Return the mtime of the newest raw *.json file for the given domain.

    Returns None if no raw files exist (domain has no source data yet).
    """
    v2_base = raw_root / _V2_BASE
    newest: float | None = None
    for subdir in _DOMAIN_RAW_SUBDIRS.get(domain, []):
        source_dir = v2_base / subdir
        if not source_dir.exists():
            continue
        for json_file in source_dir.rglob("*.json"):
            mtime = json_file.stat().st_mtime
            if newest is None or mtime > newest:
                newest = mtime
    return newest


def should_skip_domain(
    domain: str,
    raw_root: Path,
    extracted_root: Path,
    force: bool = False,
) -> bool:
    """Return True if the domain's output is up-to-date and can be skipped.

    Skips when ALL of the following are true:
    - force is False
    - extracted/<domain>/_index.json exists
    - _index.json mtime >= newest raw source file mtime

    Returns False (do not skip) when:
    - force is True
    - _index.json does not exist
    - any raw source file is newer than _index.json
    - no raw source files exist (treat as stale — domain should run and report)
    """
    if force:
        return False
    index_path = extracted_root / domain / "_index.json"
    if not index_path.exists():
        return False
    index_mtime = index_path.stat().st_mtime
    raw_newest = _newest_raw_mtime(domain, raw_root)
    if raw_newest is None:
        # No raw files found — cannot confirm up-to-date; do not skip.
        return False
    return index_mtime >= raw_newest


# ---------------------------------------------------------------------------
# Phase helpers
# ---------------------------------------------------------------------------

def find_downstream_phases(domain: str) -> list[int]:
    """Return the indices of all phases that contain `domain` or come after it.

    Example: find_downstream_phases("items") → [1, 2, 3, 4, 5]
    (Phase 1 contains "items"; phases 2-5 are downstream.)

    Returns an empty list if the domain is not found in PHASES.
    """
    for phase_idx, phase_domains in enumerate(PHASES):
        if domain in phase_domains:
            return list(range(phase_idx, len(PHASES)))
    return []


def _count_output_files(domain: str, extracted_root: Path) -> int:
    """Count the number of JSON files written in extracted/<domain>/."""
    domain_dir = extracted_root / domain
    if not domain_dir.exists():
        return 0
    return sum(1 for _ in domain_dir.glob("*.json"))


# ---------------------------------------------------------------------------
# Domain runner (called from worker thread)
# ---------------------------------------------------------------------------

def _run_domain(domain: str, raw_root: Path, extracted_root: Path) -> dict[str, Any]:
    """Import and call the domain's run() function. Returns the summary dict."""
    mod = importlib.import_module(f"pipeline.domains.{domain}")
    return mod.run(raw_root=raw_root, extracted_root=extracted_root)


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def run_pipeline(
    raw_root: Path,
    extracted_root: Path,
    force: bool = False,
    target_domain: str | None = None,
) -> int:
    """Execute the full phase pipeline.

    Args:
        raw_root: Path to raw/ directory.
        extracted_root: Path to extracted/ directory.
        force: If True, skip manifest checks and re-run all domains.
        target_domain: If set, force-run this domain and all downstream phases;
                       earlier phases use normal skip logic.

    Returns:
        Exit code: 0 on success, 1 if any domain failed.
    """
    resolver = Resolver()

    # Determine which phase indices are forced due to --domain flag.
    forced_phase_indices: set[int] = set()
    if target_domain is not None:
        downstream = find_downstream_phases(target_domain)
        if not downstream:
            print(f"[ERROR] Domain '{target_domain}' not found in PHASES.", file=sys.stderr)
            return 1
        forced_phase_indices = set(downstream)
        print(f"[orchestrator] --domain {target_domain}: forcing phases {sorted(forced_phase_indices)}")

    # Per-domain result tracking for the summary table.
    # status: "ok" | "skip" | "fail" | "blocked"
    results: dict[str, dict[str, Any]] = {d: {"status": "blocked", "count": 0} for d in _ALL_DOMAINS}

    abort_from_phase: int | None = None  # first phase index that failed

    for phase_idx, phase_domains in enumerate(PHASES):
        # Check whether this phase is blocked by an earlier failure.
        if abort_from_phase is not None and phase_idx > abort_from_phase:
            print(f"\n[orchestrator] Phase {phase_idx} SKIPPED — upstream failure in phase {abort_from_phase}")
            for domain in phase_domains:
                results[domain]["status"] = "blocked"
            continue

        # Determine per-domain force flag for this phase.
        phase_force = force or (phase_idx in forced_phase_indices)

        # Separate domains into "skip" and "run" buckets.
        domains_to_run: list[str] = []
        for domain in phase_domains:
            if should_skip_domain(domain, raw_root, extracted_root, force=phase_force):
                results[domain]["status"] = "skip"
                results[domain]["count"] = _count_output_files(domain, extracted_root)
                print(f"[{domain}] SKIP — output is up-to-date")
            else:
                domains_to_run.append(domain)

        if not domains_to_run:
            print(f"\n[orchestrator] Phase {phase_idx} — all domains up-to-date, skipping")
            continue

        print(f"\n[orchestrator] Phase {phase_idx} — running: {', '.join(domains_to_run)}")

        # Submit all domains in the phase to a thread pool.
        futures: dict[str, Future] = {}
        with ThreadPoolExecutor(max_workers=len(domains_to_run)) as executor:
            for domain in domains_to_run:
                futures[domain] = executor.submit(
                    _run_domain, domain, raw_root, extracted_root
                )
            # Collect results as futures complete (in submission order to keep
            # resolver hydration deterministic).
            for domain in domains_to_run:
                future = futures[domain]
                try:
                    summary = future.result()
                    results[domain]["status"] = "ok"
                    results[domain]["count"] = _count_output_files(domain, extracted_root)
                    results[domain]["summary"] = summary
                    print(f"[{domain}] OK — {results[domain]['count']} files")
                    # Hydrate resolver from main thread (thread safety contract).
                    resolver.load_domain(domain, extracted_root)
                except Exception as exc:  # noqa: BLE001
                    results[domain]["status"] = "fail"
                    results[domain]["error"] = str(exc)
                    print(f"[{domain}] FAIL — {exc}", file=sys.stderr)

        # If any domain in this phase failed, block all downstream phases.
        phase_failed = any(
            results[d]["status"] == "fail" for d in domains_to_run
        )
        if phase_failed and abort_from_phase is None:
            abort_from_phase = phase_idx

    # Print run summary table.
    _print_summary(results)

    any_failed = any(r["status"] == "fail" for r in results.values())
    return 1 if any_failed else 0


def _print_summary(results: dict[str, dict[str, Any]]) -> None:
    """Print a formatted summary table of all domain results."""
    print("\n" + "=" * 52)
    print(f"{'DOMAIN':<18} {'STATUS':<8} {'FILES':>6}")
    print("-" * 52)
    for domain in _ALL_DOMAINS:
        r = results.get(domain, {"status": "?", "count": 0})
        status = r.get("status", "?")
        count = r.get("count", 0)
        marker = {"ok": "[OK]  ", "skip": "[SKIP]", "fail": "[FAIL]", "blocked": "[----]"}.get(status, "[?]   ")
        print(f"{domain:<18} {marker:<8} {count:>6}")
    print("=" * 52)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dark and Darker wiki data extraction pipeline orchestrator."
    )
    parser.add_argument(
        "--domain",
        metavar="DOMAIN",
        default=None,
        help=(
            "Re-run the specified domain and all downstream phases. "
            "Earlier phases use normal skip logic. "
            f"Valid domains: {', '.join(_ALL_DOMAINS)}"
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Re-run all domains regardless of timestamps.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    exit_code = run_pipeline(
        raw_root=RAW_ROOT,
        extracted_root=EXTRACTED_ROOT,
        force=args.force,
        target_domain=args.domain,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify the module is importable (no syntax errors)**

Run from `darkanddarker-wiki/`:
```bash
py -3 -c "import pipeline.extract_all; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Verify `--help` works**

```bash
py -3 -m pipeline.extract_all --help
```
Expected: usage text showing `--domain` and `--force` flags.

---

## Chunk 2: Write Tests + Verify Full Suite

### File Map

- Create: `tests/test_extract_all.py`

---

### Task 2: Write `tests/test_extract_all.py`

**Files:**
- Create: `tests/test_extract_all.py`

- [ ] **Step 1: Write the test file**

Create `tests/test_extract_all.py` with the following content:

```python
"""Tests for pipeline/extract_all.py orchestrator.

Coverage:
- should_skip_domain() helper
- find_downstream_phases() helper
- CLI arg parsing (--domain, --force)
- Integration: phase execution order, skip logic, failure propagation
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from pipeline.extract_all import (
    PHASES,
    _ALL_DOMAINS,
    find_downstream_phases,
    should_skip_domain,
    run_pipeline,
    _parse_args,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def raw_root(tmp_path: Path) -> Path:
    """Return a tmp raw/ root directory."""
    r = tmp_path / "raw"
    r.mkdir()
    return r


@pytest.fixture()
def extracted_root(tmp_path: Path) -> Path:
    """Return a tmp extracted/ root directory."""
    e = tmp_path / "extracted"
    e.mkdir()
    return e


def _make_raw_file(raw_root: Path, v2_subpath: str, filename: str = "data.json") -> Path:
    """Create a dummy raw JSON file at raw/DungeonCrawler/.../V2/<subpath>/<filename>."""
    v2_base = raw_root / "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2"
    target = v2_base / v2_subpath
    target.mkdir(parents=True, exist_ok=True)
    f = target / filename
    f.write_text("[]", encoding="utf-8")
    return f


def _make_index(extracted_root: Path, domain: str) -> Path:
    """Create a dummy _index.json for the given domain."""
    d = extracted_root / domain
    d.mkdir(parents=True, exist_ok=True)
    idx = d / "_index.json"
    idx.write_text(json.dumps({"count": 1, "entries": []}), encoding="utf-8")
    return idx


# ---------------------------------------------------------------------------
# should_skip_domain()
# ---------------------------------------------------------------------------

class TestShouldSkipDomain:
    def test_returns_false_when_index_missing(self, raw_root, extracted_root):
        """No _index.json → always run."""
        _make_raw_file(raw_root, "Quest/Quest", "Id_Quest_01.json")
        assert should_skip_domain("quests", raw_root, extracted_root, force=False) is False

    def test_returns_true_when_index_newer_than_raw(self, raw_root, extracted_root):
        """_index.json newer than all raw files → skip."""
        import time
        raw_file = _make_raw_file(raw_root, "Quest/Quest", "Id_Quest_01.json")
        # Touch index file after raw file to ensure index is newer.
        time.sleep(0.01)
        idx = _make_index(extracted_root, "quests")
        # Sanity check: index is actually newer.
        assert idx.stat().st_mtime >= raw_file.stat().st_mtime
        assert should_skip_domain("quests", raw_root, extracted_root, force=False) is True

    def test_returns_false_when_raw_newer_than_index(self, raw_root, extracted_root):
        """Raw file newer than _index.json → do not skip."""
        import time
        idx = _make_index(extracted_root, "quests")
        time.sleep(0.01)
        _make_raw_file(raw_root, "Quest/Quest", "Id_Quest_01.json")
        assert should_skip_domain("quests", raw_root, extracted_root, force=False) is False

    def test_returns_false_when_force_true_even_if_index_newer(self, raw_root, extracted_root):
        """force=True overrides skip logic."""
        import time
        _make_raw_file(raw_root, "Quest/Quest", "Id_Quest_01.json")
        time.sleep(0.01)
        _make_index(extracted_root, "quests")
        assert should_skip_domain("quests", raw_root, extracted_root, force=True) is False

    def test_returns_false_when_no_raw_files_exist(self, raw_root, extracted_root):
        """No raw files at all → treat as stale (cannot confirm up-to-date)."""
        _make_index(extracted_root, "quests")
        assert should_skip_domain("quests", raw_root, extracted_root, force=False) is False


# ---------------------------------------------------------------------------
# find_downstream_phases()
# ---------------------------------------------------------------------------

class TestFindDownstreamPhases:
    def test_engine_returns_all_phases(self):
        """engine is in phase 0 → returns [0, 1, 2, 3, 4, 5]."""
        result = find_downstream_phases("engine")
        assert result == list(range(len(PHASES)))

    def test_items_returns_from_phase1(self):
        """items is in phase 1 → returns [1, 2, 3, 4, 5]."""
        result = find_downstream_phases("items")
        assert result == list(range(1, len(PHASES)))

    def test_quests_returns_last_phase_only(self):
        """quests is in the last phase → returns [last_idx]."""
        last_idx = len(PHASES) - 1
        result = find_downstream_phases("quests")
        assert result == [last_idx]

    def test_economy_returns_correct_phase(self):
        """economy is in phase 4 → returns [4, 5]."""
        result = find_downstream_phases("economy")
        assert result == [4, 5]

    def test_unknown_domain_returns_empty_list(self):
        """Unknown domain → empty list."""
        result = find_downstream_phases("nonexistent_domain")
        assert result == []

    def test_all_domains_found_in_phases(self):
        """Every domain in _ALL_DOMAINS must be findable."""
        for domain in _ALL_DOMAINS:
            result = find_downstream_phases(domain)
            assert len(result) > 0, f"Domain '{domain}' not found in PHASES"


# ---------------------------------------------------------------------------
# CLI arg parsing
# ---------------------------------------------------------------------------

class TestArgParsing:
    def test_defaults_when_no_flags(self):
        args = _parse_args([])
        assert args.domain is None
        assert args.force is False

    def test_force_flag(self):
        args = _parse_args(["--force"])
        assert args.force is True
        assert args.domain is None

    def test_domain_flag(self):
        args = _parse_args(["--domain", "items"])
        assert args.domain == "items"
        assert args.force is False

    def test_force_and_domain_together(self):
        args = _parse_args(["--force", "--domain", "combat"])
        assert args.force is True
        assert args.domain == "combat"


# ---------------------------------------------------------------------------
# Integration: run_pipeline()
# ---------------------------------------------------------------------------

def _make_mock_run(summary: dict | None = None):
    """Return a mock run() function that returns a summary dict."""
    return MagicMock(return_value=summary or {"entities": 1})


def _patch_domain(domain: str, summary: dict | None = None):
    """Return a patch context manager for pipeline.domains.<domain>.run."""
    mock_mod = MagicMock()
    mock_mod.run = _make_mock_run(summary)
    return patch(f"pipeline.extract_all.importlib.import_module", return_value=mock_mod)


class TestRunPipelineIntegration:
    """Integration tests using mocked domain run() functions.

    Strategy: patch importlib.import_module so every domain returns a mock
    module whose run() we can assert was called. We also patch
    should_skip_domain to control skip behaviour cleanly.
    """

    def _make_mock_import(self, per_domain_summaries: dict[str, dict] | None = None):
        """Return a side_effect function for importlib.import_module.

        per_domain_summaries: optional map of domain → summary dict.
        """
        summaries = per_domain_summaries or {}

        def _import(module_path: str):
            # module_path is "pipeline.domains.<domain>"
            domain = module_path.split(".")[-1]
            mock_mod = MagicMock()
            mock_mod.run = MagicMock(return_value=summaries.get(domain, {"entities": 1}))
            return mock_mod

        return _import

    def test_all_phases_run_when_no_skip(self, raw_root, extracted_root):
        """All domains are called when skip returns False everywhere."""
        called_domains = []

        def _import(module_path: str):
            domain = module_path.split(".")[-1]
            mock_mod = MagicMock()

            def _run(raw_root, extracted_root):
                called_domains.append(domain)
                # Write a dummy _index.json so _count_output_files works.
                d = extracted_root / domain
                d.mkdir(parents=True, exist_ok=True)
                (d / "_index.json").write_text("{}", encoding="utf-8")
                return {"entities": 1}

            mock_mod.run = _run
            return mock_mod

        with patch("pipeline.extract_all.importlib.import_module", side_effect=_import):
            with patch("pipeline.extract_all.should_skip_domain", return_value=False):
                with patch.object(
                    __import__("pipeline.core.resolver", fromlist=["Resolver"]).Resolver,
                    "load_domain",
                ):
                    exit_code = run_pipeline(raw_root, extracted_root)

        assert exit_code == 0
        assert set(called_domains) == set(_ALL_DOMAINS)

    def test_phase_execution_order_respects_phases(self, raw_root, extracted_root):
        """engine must complete before items/classes/monsters are called."""
        call_order = []

        def _import(module_path: str):
            domain = module_path.split(".")[-1]
            mock_mod = MagicMock()

            def _run(raw_root, extracted_root):
                call_order.append(domain)
                d = extracted_root / domain
                d.mkdir(parents=True, exist_ok=True)
                (d / "_index.json").write_text("{}", encoding="utf-8")
                return {}

            mock_mod.run = _run
            return mock_mod

        with patch("pipeline.extract_all.importlib.import_module", side_effect=_import):
            with patch("pipeline.extract_all.should_skip_domain", return_value=False):
                with patch.object(
                    __import__("pipeline.core.resolver", fromlist=["Resolver"]).Resolver,
                    "load_domain",
                ):
                    run_pipeline(raw_root, extracted_root)

        # engine must appear before any phase-2 domain.
        phase2_domains = {"items", "classes", "monsters"}
        engine_idx = call_order.index("engine")
        for d in phase2_domains:
            if d in call_order:
                assert call_order.index(d) > engine_idx, (
                    f"{d} ran before engine in call_order={call_order}"
                )

    def test_skip_logic_prevents_domain_run(self, raw_root, extracted_root):
        """Domains where should_skip_domain returns True must not call run()."""
        called = []

        def _import(module_path: str):
            domain = module_path.split(".")[-1]
            mock_mod = MagicMock()

            def _run(raw_root, extracted_root):
                called.append(domain)
                d = extracted_root / domain
                d.mkdir(parents=True, exist_ok=True)
                (d / "_index.json").write_text("{}", encoding="utf-8")
                return {}

            mock_mod.run = _run
            return mock_mod

        # Skip everything.
        def _skip(domain, raw_root, extracted_root, force=False):
            # Create dummy output so _count_output_files works.
            d = extracted_root / domain
            d.mkdir(parents=True, exist_ok=True)
            (d / "_index.json").write_text("{}", encoding="utf-8")
            return True

        with patch("pipeline.extract_all.importlib.import_module", side_effect=_import):
            with patch("pipeline.extract_all.should_skip_domain", side_effect=_skip):
                exit_code = run_pipeline(raw_root, extracted_root)

        assert exit_code == 0
        assert called == [], f"Expected no domains to run, but got: {called}"

    def test_failure_in_phase_blocks_downstream_phases(self, raw_root, extracted_root):
        """A domain failure in phase 1 must prevent phase 2+ from running."""
        called = []

        def _import(module_path: str):
            domain = module_path.split(".")[-1]
            mock_mod = MagicMock()

            def _run(raw_root, extracted_root):
                called.append(domain)
                if domain == "engine":
                    raise RuntimeError("engine extraction failed")
                d = extracted_root / domain
                d.mkdir(parents=True, exist_ok=True)
                (d / "_index.json").write_text("{}", encoding="utf-8")
                return {}

            mock_mod.run = _run
            return mock_mod

        with patch("pipeline.extract_all.importlib.import_module", side_effect=_import):
            with patch("pipeline.extract_all.should_skip_domain", return_value=False):
                with patch.object(
                    __import__("pipeline.core.resolver", fromlist=["Resolver"]).Resolver,
                    "load_domain",
                ):
                    exit_code = run_pipeline(raw_root, extracted_root)

        assert exit_code == 1
        # engine was called and failed; no phase-2+ domains should have run.
        phase2_plus = {"items", "classes", "monsters", "combat", "spells", "status",
                       "dungeons", "spawns", "economy", "quests"}
        called_set = set(called)
        assert called_set.isdisjoint(phase2_plus), (
            f"Downstream domains ran despite phase-0 failure: {called_set & phase2_plus}"
        )

    def test_failure_in_phase2_blocks_phases_3_plus_not_phase1(self, raw_root, extracted_root):
        """Failure in phase 2 (items) must not block phase 1 (engine) and must block phases 3+."""
        called = []

        def _import(module_path: str):
            domain = module_path.split(".")[-1]
            mock_mod = MagicMock()

            def _run(raw_root, extracted_root):
                called.append(domain)
                if domain == "items":
                    raise RuntimeError("items extraction failed")
                d = extracted_root / domain
                d.mkdir(parents=True, exist_ok=True)
                (d / "_index.json").write_text("{}", encoding="utf-8")
                return {}

            mock_mod.run = _run
            return mock_mod

        with patch("pipeline.extract_all.importlib.import_module", side_effect=_import):
            with patch("pipeline.extract_all.should_skip_domain", return_value=False):
                with patch.object(
                    __import__("pipeline.core.resolver", fromlist=["Resolver"]).Resolver,
                    "load_domain",
                ):
                    exit_code = run_pipeline(raw_root, extracted_root)

        assert exit_code == 1
        assert "engine" in called  # phase 1 completed before the failure
        # Phase 3+ domains must not have run.
        phase3_plus = {"combat", "spells", "status", "dungeons", "spawns", "economy", "quests"}
        assert set(called).isdisjoint(phase3_plus), (
            f"Phase 3+ domains ran despite phase-2 failure: {set(called) & phase3_plus}"
        )

    def test_domain_flag_forces_target_and_downstream(self, raw_root, extracted_root):
        """--domain items forces phases 1+ to run; phase 0 (engine) uses skip logic."""
        should_skip_calls: list[tuple] = []
        called = []

        def _fake_skip(domain, raw_root, extracted_root, force=False):
            should_skip_calls.append((domain, force))
            # Simulate: engine is up-to-date (would skip), everything else runs.
            if domain == "engine":
                idx = extracted_root / "engine" / "_index.json"
                idx.parent.mkdir(parents=True, exist_ok=True)
                idx.write_text("{}", encoding="utf-8")
                return True
            return False

        def _import(module_path: str):
            domain = module_path.split(".")[-1]
            mock_mod = MagicMock()

            def _run(raw_root, extracted_root):
                called.append(domain)
                d = extracted_root / domain
                d.mkdir(parents=True, exist_ok=True)
                (d / "_index.json").write_text("{}", encoding="utf-8")
                return {}

            mock_mod.run = _run
            return mock_mod

        with patch("pipeline.extract_all.importlib.import_module", side_effect=_import):
            with patch("pipeline.extract_all.should_skip_domain", side_effect=_fake_skip):
                with patch.object(
                    __import__("pipeline.core.resolver", fromlist=["Resolver"]).Resolver,
                    "load_domain",
                ):
                    exit_code = run_pipeline(
                        raw_root, extracted_root, force=False, target_domain="items"
                    )

        assert exit_code == 0
        # engine was skipped (phase 0 uses normal skip logic and _fake_skip returns True for it).
        assert "engine" not in called
        # items and all downstream phase domains ran.
        downstream_domains = {d for phase_idx, phase in enumerate(PHASES) for d in phase if phase_idx >= 1}
        assert downstream_domains.issubset(set(called)), (
            f"Expected all downstream domains to run. called={called}"
        )

    def test_force_flag_bypasses_skip_for_all_domains(self, raw_root, extracted_root):
        """--force means should_skip_domain is called with force=True for every domain."""
        skip_force_values: list[bool] = []

        def _fake_skip(domain, raw_root, extracted_root, force=False):
            skip_force_values.append(force)
            return False  # never actually skip

        def _import(module_path: str):
            domain = module_path.split(".")[-1]
            mock_mod = MagicMock()

            def _run(raw_root, extracted_root):
                d = extracted_root / domain
                d.mkdir(parents=True, exist_ok=True)
                (d / "_index.json").write_text("{}", encoding="utf-8")
                return {}

            mock_mod.run = _run
            return mock_mod

        with patch("pipeline.extract_all.importlib.import_module", side_effect=_import):
            with patch("pipeline.extract_all.should_skip_domain", side_effect=_fake_skip):
                with patch.object(
                    __import__("pipeline.core.resolver", fromlist=["Resolver"]).Resolver,
                    "load_domain",
                ):
                    run_pipeline(raw_root, extracted_root, force=True)

        assert all(v is True for v in skip_force_values), (
            f"Expected all skip checks to use force=True, got: {skip_force_values}"
        )
```

- [ ] **Step 2: Run the test suite and confirm all tests pass**

Run from `darkanddarker-wiki/`:
```bash
py -3 -m pytest tests/test_extract_all.py -v
```

Expected output (all green):
```
tests/test_extract_all.py::TestShouldSkipDomain::test_returns_false_when_index_missing PASSED
tests/test_extract_all.py::TestShouldSkipDomain::test_returns_true_when_index_newer_than_raw PASSED
tests/test_extract_all.py::TestShouldSkipDomain::test_returns_false_when_raw_newer_than_index PASSED
tests/test_extract_all.py::TestShouldSkipDomain::test_returns_false_when_force_true_even_if_index_newer PASSED
tests/test_extract_all.py::TestShouldSkipDomain::test_returns_false_when_no_raw_files_exist PASSED
tests/test_extract_all.py::TestFindDownstreamPhases::test_engine_returns_all_phases PASSED
tests/test_extract_all.py::TestFindDownstreamPhases::test_items_returns_from_phase1 PASSED
tests/test_extract_all.py::TestFindDownstreamPhases::test_quests_returns_last_phase_only PASSED
tests/test_extract_all.py::TestFindDownstreamPhases::test_economy_returns_correct_phase PASSED
tests/test_extract_all.py::TestFindDownstreamPhases::test_unknown_domain_returns_empty_list PASSED
tests/test_extract_all.py::TestFindDownstreamPhases::test_all_domains_found_in_phases PASSED
tests/test_extract_all.py::TestArgParsing::test_defaults_when_no_flags PASSED
tests/test_extract_all.py::TestArgParsing::test_force_flag PASSED
tests/test_extract_all.py::TestArgParsing::test_domain_flag PASSED
tests/test_extract_all.py::TestArgParsing::test_force_and_domain_together PASSED
tests/test_extract_all.py::TestRunPipelineIntegration::test_all_phases_run_when_no_skip PASSED
tests/test_extract_all.py::TestRunPipelineIntegration::test_phase_execution_order_respects_phases PASSED
tests/test_extract_all.py::TestRunPipelineIntegration::test_skip_logic_prevents_domain_run PASSED
tests/test_extract_all.py::TestRunPipelineIntegration::test_failure_in_phase_blocks_downstream_phases PASSED
tests/test_extract_all.py::TestRunPipelineIntegration::test_failure_in_phase2_blocks_phases_3_plus_not_phase1 PASSED
tests/test_extract_all.py::TestRunPipelineIntegration::test_domain_flag_forces_target_and_downstream PASSED
tests/test_extract_all.py::TestRunPipelineIntegration::test_force_flag_bypasses_skip_for_all_domains PASSED

22 passed in ...
```

If any test fails, diagnose and fix the implementation before proceeding.

- [ ] **Step 3: Run the full test suite to confirm no regressions**

```bash
py -3 -m pytest --tb=short -q
```

Expected: all previously passing tests still pass; the 22 new tests pass too. Zero failures.

- [ ] **Step 4: Commit**

```bash
git add pipeline/extract_all.py tests/test_extract_all.py
git commit -m "feat: rewrite extract_all.py as phase-based orchestrator with parallel execution, skip logic, and --domain/--force CLI flags"
```

---

## Notes for Implementers

### Resolver signature
`pipeline/core/resolver.py` `load_domain()` takes two arguments: `domain: str` and `extracted_root: Path`. Call it as:
```python
resolver.load_domain(domain, extracted_root)
```
This differs from the spec prose which implies a single argument — the actual implementation (as of Phase 1) requires both.

### Thread safety
Worker threads call `mod.run()`. The main thread calls `future.result()` sequentially (in submission order) and then calls `resolver.load_domain()`. This means resolver hydration is always main-thread-only, satisfying `core/resolver.py`'s documented contract.

### cosmetics domain
`cosmetics` is in the spec's PHASES but is not yet implemented. It is intentionally excluded from `PHASES` in this orchestrator. When `cosmetics` is implemented, add `"cosmetics"` to the last phase entry: `["quests", "cosmetics"]`.

### Failure propagation detail
If multiple domains in a phase fail (e.g. both `items` and `classes` fail in phase 2), `abort_from_phase` is set to that phase index and all subsequent phases are marked `blocked`. Sibling domains within the same phase that were submitted before the failure are allowed to complete normally — they run in threads and cannot be cancelled mid-flight.
