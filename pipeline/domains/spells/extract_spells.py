"""Extract DCSpellDataAsset files → extracted/spells/<id>.json + _index.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_text, resolve_tag
from pipeline.core.writer import Writer


def extract_spell(file_path: Path) -> dict | None:
    """Extract one DCSpellDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCSpellDataAsset"), None)
    if not obj:
        return None

    spell_id = obj.get("Name", file_path.stem)
    props = get_properties(obj)

    return {
        "id": spell_id,
        "name": resolve_text(props.get("Name")),
        "description": resolve_text(props.get("Desc")),
        "casting_type": resolve_tag(props.get("CastingType")),
        "source_type": resolve_tag(props.get("SourceType")),
        "cost_type": resolve_tag(props.get("CostType")),
        "range": props.get("Range"),
        "area_radius": props.get("AreaRadius"),
        "spell_tag": resolve_tag(props.get("SpellTag")),
    }


def run_spells(spell_dir: Path, extracted_root: Path) -> dict:
    """Extract all Spell files → extracted/spells/<id>.json + _index.json."""
    files = find_files(str(Path(spell_dir) / "Id_Spell_*.json"))
    print(f"  [spells] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    spells = {}

    for f in files:
        result = extract_spell(f)
        if not result:
            continue
        spell_id = result["id"]
        spells[spell_id] = result
        writer.write_entity("spells", spell_id, result, source_files=[str(f)])
        index_entries.append({
            "id": spell_id,
            "name": result.get("name"),
            "source_type": result.get("source_type"),
            "spell_tag": result.get("spell_tag"),
        })

    writer.write_index("spells", index_entries)
    print(f"  [spells] Extracted {len(spells)} spells")
    return spells
