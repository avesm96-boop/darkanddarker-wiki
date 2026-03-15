"""Classes domain extractor — run() called by extract_all.py orchestrator."""
from pathlib import Path

from pipeline.domains.classes.extract_player_characters import run_player_characters
from pipeline.domains.classes.extract_perks import run_perks
from pipeline.domains.classes.extract_skills import run_skills
from pipeline.domains.classes.extract_shapeshifts import run_shapeshifts
from pipeline.core.writer import Writer

_V2_BASE = "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2"


def run(raw_root: Path, extracted_root: Path) -> dict:
    """Run all classes domain extractors. Returns summary of counts.

    NOTE: Individual run_* functions each write a partial _index.json as a
    side-effect (useful for standalone runs / unit tests). This orchestrator
    overwrites that partial index with a single combined index containing all
    entity types at the end.
    """
    print("[classes] Starting extraction...")
    summary = {}
    all_entities: dict[str, dict] = {}

    dirs = {
        "pc": raw_root / _V2_BASE / "PlayerCharacter" / "PlayerCharacterEffect",
        "perk": raw_root / _V2_BASE / "Perk" / "Perk",
        "skill": raw_root / _V2_BASE / "Skill" / "Skill",
        "shapeshift": raw_root / _V2_BASE / "ShapeShift" / "ShapeShift",
    }

    if dirs["pc"].exists():
        pcs = run_player_characters(pc_dir=dirs["pc"], extracted_root=extracted_root)
        summary["player_characters"] = len(pcs)
        all_entities.update({k: {**v, "_entity_type": "player_character"}
                             for k, v in pcs.items()})
    else:
        print(f"  [classes] WARNING: {dirs['pc']} not found")
        summary["player_characters"] = 0

    if dirs["perk"].exists():
        perks = run_perks(perk_dir=dirs["perk"], extracted_root=extracted_root)
        summary["perks"] = len(perks)
        all_entities.update({k: {**v, "_entity_type": "perk"}
                             for k, v in perks.items()})
    else:
        print(f"  [classes] WARNING: {dirs['perk']} not found")
        summary["perks"] = 0

    if dirs["skill"].exists():
        skills = run_skills(skill_dir=dirs["skill"], extracted_root=extracted_root)
        summary["skills"] = len(skills)
        all_entities.update({k: {**v, "_entity_type": "skill"}
                             for k, v in skills.items()})
    else:
        print(f"  [classes] WARNING: {dirs['skill']} not found")
        summary["skills"] = 0

    if dirs["shapeshift"].exists():
        ss = run_shapeshifts(ss_dir=dirs["shapeshift"], extracted_root=extracted_root)
        summary["shapeshifts"] = len(ss)
        all_entities.update({k: {**v, "_entity_type": "shapeshift"}
                             for k, v in ss.items()})
    else:
        print(f"  [classes] WARNING: {dirs['shapeshift']} not found")
        summary["shapeshifts"] = 0

    # Write combined index with ALL entity types (overwrites partial indexes
    # written by individual run_* functions above)
    combined_index = [
        {"id": v["id"], "name": v.get("name"), "type": v["_entity_type"]}
        for v in all_entities.values()
    ]
    Writer(extracted_root).write_index("classes", combined_index)

    print(f"[classes] Done. Summary: {summary}")
    return summary
