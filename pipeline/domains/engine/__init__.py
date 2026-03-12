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
