"""Spells domain extractor — run() called by extract_all.py orchestrator."""
from pathlib import Path

from pipeline.domains.spells.extract_spells import run_spells
from pipeline.domains.spells.extract_religions import run_religions
from pipeline.domains.spells.extract_faustian_bargains import run_faustian_bargains
from pipeline.core.writer import Writer

_V2_BASE = "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2"


def run(raw_root: Path, extracted_root: Path) -> dict:
    """Run all spells domain extractors. Returns summary of counts.

    NOTE: Individual run_* functions each write a partial _index.json as a
    side-effect (useful for standalone runs / unit tests). This orchestrator
    overwrites that partial index with a single combined index containing all
    entity types at the end.
    """
    print("[spells] Starting extraction...")
    summary = {}
    all_entities: dict[str, dict] = {}

    dirs = {
        "spell": raw_root / _V2_BASE / "Spell" / "Spell",
        "religion": raw_root / _V2_BASE / "Religion" / "Religion",
        "fb": raw_root / _V2_BASE / "FaustianBargain" / "FaustianBargain",
    }

    if dirs["spell"].exists():
        spells = run_spells(spell_dir=dirs["spell"], extracted_root=extracted_root)
        summary["spells"] = len(spells)
        all_entities.update({k: {**v, "_entity_type": "spell"}
                             for k, v in spells.items()})
    else:
        print(f"  [spells] WARNING: {dirs['spell']} not found")
        summary["spells"] = 0

    if dirs["religion"].exists():
        religions = run_religions(religion_dir=dirs["religion"], extracted_root=extracted_root)
        summary["religions"] = len(religions)
        all_entities.update({k: {**v, "_entity_type": "religion"}
                             for k, v in religions.items()})
    else:
        print(f"  [spells] WARNING: {dirs['religion']} not found")
        summary["religions"] = 0

    if dirs["fb"].exists():
        fbs = run_faustian_bargains(fb_dir=dirs["fb"], extracted_root=extracted_root)
        summary["faustian_bargains"] = len(fbs)
        all_entities.update({k: {**v, "_entity_type": "faustian_bargain"}
                             for k, v in fbs.items()})
    else:
        print(f"  [spells] WARNING: {dirs['fb']} not found")
        summary["faustian_bargains"] = 0

    # Write combined index with ALL entity types (overwrites partial indexes
    # written by individual run_* functions above)
    combined_index = [
        {"id": v["id"], "name": v.get("name"), "type": v["_entity_type"]}
        for v in all_entities.values()
    ]
    Writer(extracted_root).write_index("spells", combined_index)

    print(f"[spells] Done. Summary: {summary}")
    return summary
