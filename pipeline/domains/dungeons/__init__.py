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

    # Single-directory extractors: each run_*() gets one dir and returns {id: entity}
    # _entity_type is added here when merging into all_entities for the combined index
    for key, fn, dir_key, entity_type, param in [
        ("dungeons",           run_dungeons,           "dungeon",           "dungeon",           "dungeon_dir"),
        ("dungeon_types",      run_dungeon_types,      "dungeon_type",      "dungeon_type",      "dungeon_type_dir"),
        ("dungeon_grades",     run_dungeon_grades,     "dungeon_grade",     "dungeon_grade",     "dungeon_grade_dir"),
        ("dungeon_cards",      run_dungeon_cards,      "dungeon_card",      "dungeon_card",      "dungeon_card_dir"),
        ("dungeon_layouts",    run_dungeon_layouts,    "dungeon_layout",    "dungeon_layout",    "dungeon_layout_dir"),
        ("dungeon_modules",    run_dungeon_modules,    "dungeon_module",    "dungeon_module",    "dungeon_module_dir"),
        ("props",              run_props,              "props",             "prop",              "props_dir"),
        ("props_effects",      run_props_effects,      "props_effect",      "props_effect",      "props_effect_dir"),
        ("props_interacts",    run_props_interacts,    "props_interact",    "props_interact",    "props_interact_dir"),
        ("props_skill_checks", run_props_skill_checks, "props_skill_check", "props_skill_check", "props_skill_check_dir"),
        ("map_icons",          run_map_icons,          "map_icon",          "map_icon",          "map_icon_dir"),
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

    # Multi-subdir extractors: run_floor_rules and run_vehicles already tag entities
    # with _entity_type internally, so merge directly.
    floor_rule_dir = dirs["floor_rule"]
    if floor_rule_dir.exists():
        rules = run_floor_rules(floor_rule_dir=floor_rule_dir, extracted_root=extracted_root)
        summary["floor_rules"] = len(rules)
        all_entities.update(rules)
    else:
        print(f"  [dungeons] WARNING: {floor_rule_dir} not found")
        summary["floor_rules"] = 0

    vehicle_dir = dirs["vehicle"]
    if vehicle_dir.exists():
        vehicles = run_vehicles(vehicle_dir=vehicle_dir, extracted_root=extracted_root)
        summary["vehicles"] = len(vehicles)
        all_entities.update(vehicles)
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
