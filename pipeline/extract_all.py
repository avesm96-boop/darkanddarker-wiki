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

_V2_BASE = "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2"

# ---------------------------------------------------------------------------
# Phase definition
# ---------------------------------------------------------------------------

PHASES: list[list[str]] = [
    ["engine"],
    ["items", "classes", "monsters"],
    ["combat", "spells", "status"],
    ["dungeons", "spawns"],
    ["economy"],
    ["quests"],
]

_ALL_DOMAINS: list[str] = [d for phase in PHASES for d in phase]

# ---------------------------------------------------------------------------
# Raw source directories per domain (for mtime skip checks)
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
        "FloorRule",
        "Props/Props",
        "MapIcon/MapIcon",
        "Vehicle/Vehicle",
    ],
    "spawns": [
        "Spawner/Spawner",
        "LootDrop/LootDrop",
    ],
    "economy": [
        "Merchant/BaseGear",
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
    """Return the mtime of the newest raw *.json file for the given domain."""
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
    """Return True if the domain output is up-to-date and can be skipped."""
    if force:
        return False
    index_path = extracted_root / domain / "_index.json"
    if not index_path.exists():
        return False
    index_mtime = index_path.stat().st_mtime
    raw_newest = _newest_raw_mtime(domain, raw_root)
    if raw_newest is None:
        return False
    return index_mtime >= raw_newest


# ---------------------------------------------------------------------------
# Phase helpers
# ---------------------------------------------------------------------------

def find_downstream_phases(domain: str) -> list[int]:
    """Return indices of all phases containing or after the given domain."""
    for phase_idx, phase_domains in enumerate(PHASES):
        if domain in phase_domains:
            return list(range(phase_idx, len(PHASES)))
    return []


def _count_output_files(domain: str, extracted_root: Path) -> int:
    """Count JSON files in extracted/<domain>/."""
    domain_dir = extracted_root / domain
    if not domain_dir.exists():
        return 0
    return sum(1 for _ in domain_dir.glob("*.json"))


# ---------------------------------------------------------------------------
# Domain runner (called from worker thread)
# ---------------------------------------------------------------------------

def _run_domain(domain: str, raw_root: Path, extracted_root: Path) -> dict[str, Any]:
    """Import and call the domain's run() function."""
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
    """Execute the full phase pipeline. Returns exit code (0=success, 1=failure)."""
    resolver = Resolver()

    forced_phase_indices: set[int] = set()
    if target_domain is not None:
        downstream = find_downstream_phases(target_domain)
        if not downstream:
            print(f"[ERROR] Domain '{target_domain}' not found in PHASES.", file=sys.stderr)
            return 1
        forced_phase_indices = set(downstream)
        print(f"[orchestrator] --domain {target_domain}: forcing phases {sorted(forced_phase_indices)}")

    results: dict[str, dict[str, Any]] = {d: {"status": "blocked", "count": 0} for d in _ALL_DOMAINS}
    abort_from_phase: int | None = None

    for phase_idx, phase_domains in enumerate(PHASES):
        if abort_from_phase is not None and phase_idx > abort_from_phase:
            print(f"\n[orchestrator] Phase {phase_idx} SKIPPED — upstream failure in phase {abort_from_phase}")
            for domain in phase_domains:
                results[domain]["status"] = "blocked"
            continue

        phase_force = force or (phase_idx in forced_phase_indices)

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

        futures: dict[str, Future] = {}
        with ThreadPoolExecutor(max_workers=len(domains_to_run)) as executor:
            for domain in domains_to_run:
                futures[domain] = executor.submit(
                    _run_domain, domain, raw_root, extracted_root
                )
            for domain in domains_to_run:
                future = futures[domain]
                try:
                    summary = future.result()
                    results[domain]["status"] = "ok"
                    results[domain]["count"] = _count_output_files(domain, extracted_root)
                    results[domain]["summary"] = summary
                    print(f"[{domain}] OK — {results[domain]['count']} files")
                    resolver.load_domain(domain, extracted_root)
                except Exception as exc:  # noqa: BLE001
                    results[domain]["status"] = "fail"
                    results[domain]["error"] = str(exc)
                    print(f"[{domain}] FAIL — {exc}", file=sys.stderr)

        phase_failed = any(results[d]["status"] == "fail" for d in domains_to_run)
        if phase_failed and abort_from_phase is None:
            abort_from_phase = phase_idx

    _print_summary(results)
    any_failed = any(r["status"] == "fail" for r in results.values())
    return 1 if any_failed else 0


def _print_summary(results: dict[str, dict[str, Any]]) -> None:
    """Print a formatted summary table."""
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
