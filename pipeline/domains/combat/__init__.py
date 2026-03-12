"""Combat domain extractor — run() called by extract_all.py orchestrator."""
from pathlib import Path

from pipeline.domains.combat.extract_melee_attacks import run_melee_attacks
from pipeline.domains.combat.extract_movement_modifiers import run_movement_modifiers
from pipeline.domains.combat.extract_ge_modifiers import run_ge_modifiers
from pipeline.domains.combat.extract_projectiles import run_projectiles
from pipeline.domains.combat.extract_aoes import run_aoes
from pipeline.core.writer import Writer

_V2_BASE = "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2"


def run(raw_root: Path, extracted_root: Path) -> dict:
    """Run all combat domain extractors. Returns summary of counts.

    NOTE: Individual run_* functions each write a partial _index.json as a
    side-effect (useful for standalone runs / unit tests). This orchestrator
    overwrites that partial index with a single combined index containing all
    entity types at the end.
    """
    print("[combat] Starting extraction...")
    summary = {}
    all_entities: dict[str, dict] = {}

    dirs = {
        "melee": raw_root / _V2_BASE / "MeleeAttack" / "MeleeAttack",
        "mm": raw_root / _V2_BASE / "MovementModifier" / "MovementModifier",
        "ge": raw_root / _V2_BASE / "GEModifier" / "GEModifier",
        "projectile": raw_root / _V2_BASE / "Projectile",
        "aoe": raw_root / _V2_BASE / "Aoe" / "Aoe",
    }

    if dirs["melee"].exists():
        attacks = run_melee_attacks(melee_dir=dirs["melee"], extracted_root=extracted_root)
        summary["melee_attacks"] = len(attacks)
        all_entities.update({k: {**v, "_entity_type": "melee_attack"}
                             for k, v in attacks.items()})
    else:
        print(f"  [combat] WARNING: {dirs['melee']} not found")
        summary["melee_attacks"] = 0

    if dirs["mm"].exists():
        mms = run_movement_modifiers(mm_dir=dirs["mm"], extracted_root=extracted_root)
        summary["movement_modifiers"] = len(mms)
        all_entities.update({k: {**v, "_entity_type": "movement_modifier"}
                             for k, v in mms.items()})
    else:
        print(f"  [combat] WARNING: {dirs['mm']} not found")
        summary["movement_modifiers"] = 0

    if dirs["ge"].exists():
        ges = run_ge_modifiers(ge_dir=dirs["ge"], extracted_root=extracted_root)
        summary["ge_modifiers"] = len(ges)
        all_entities.update({k: {**v, "_entity_type": "ge_modifier"}
                             for k, v in ges.items()})
    else:
        print(f"  [combat] WARNING: {dirs['ge']} not found")
        summary["ge_modifiers"] = 0

    if dirs["projectile"].exists():
        projs = run_projectiles(projectile_dir=dirs["projectile"], extracted_root=extracted_root)
        summary["projectiles"] = len(projs)
        all_entities.update({k: {**v, "_entity_type": "projectile"}
                             for k, v in projs.items()})
    else:
        print(f"  [combat] WARNING: {dirs['projectile']} not found")
        summary["projectiles"] = 0

    if dirs["aoe"].exists():
        aoes = run_aoes(aoe_dir=dirs["aoe"], extracted_root=extracted_root)
        summary["aoes"] = len(aoes)
        all_entities.update({k: {**v, "_entity_type": "aoe"}
                             for k, v in aoes.items()})
    else:
        print(f"  [combat] WARNING: {dirs['aoe']} not found")
        summary["aoes"] = 0

    # Write combined index with ALL entity types (overwrites partial indexes
    # written by individual run_* functions above)
    combined_index = [
        {"id": v["id"], "type": v["_entity_type"]}
        for v in all_entities.values()
    ]
    Writer(extracted_root).write_index("combat", combined_index)

    print(f"[combat] Done. Summary: {summary}")
    return summary
