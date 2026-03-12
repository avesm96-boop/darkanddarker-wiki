"""Extract DCGEModifierDataAsset files → extracted/combat/<id>.json + _index.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_tag
from pipeline.core.writer import Writer


def extract_ge_modifier(file_path: Path) -> dict | None:
    """Extract one DCGEModifierDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCGEModifierDataAsset"), None)
    if not obj:
        return None

    ge_id = obj.get("Name", file_path.stem)
    props = get_properties(obj)

    return {
        "id": ge_id,
        "target_gameplay_effect_tag": resolve_tag(props.get("TargetGameplayEffectTag")),
        "effect_type": resolve_tag(props.get("EffectType")),
        "add": props.get("Add"),
    }


def run_ge_modifiers(ge_dir: Path, extracted_root: Path) -> dict:
    """Extract all GEModifier files → extracted/combat/<id>.json + _index.json."""
    files = find_files(str(Path(ge_dir) / "Id_GEModifier_*.json"))
    print(f"  [ge_modifiers] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    modifiers = {}

    for f in files:
        result = extract_ge_modifier(f)
        if not result:
            continue
        ge_id = result["id"]
        modifiers[ge_id] = result
        writer.write_entity("combat", ge_id, result, source_files=[str(f)])
        index_entries.append({
            "id": ge_id,
            "target_gameplay_effect_tag": result.get("target_gameplay_effect_tag"),
            "effect_type": result.get("effect_type"),
        })

    writer.write_index("combat", index_entries)
    print(f"  [ge_modifiers] Extracted {len(modifiers)} GE modifiers")
    return modifiers
