"""Extract DCGameplayEffectDataAsset (player class base stats) files.

Output: extracted/classes/<id>.json + extracted/classes/_index.json
"""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.writer import Writer
from pipeline.core.normalizer import camel_to_snake

_STAT_FIELDS = (
    "StrengthBase", "VigorBase", "AgilityBase", "DexterityBase",
    "WillBase", "KnowledgeBase", "ResourcefulnessBase", "MoveSpeedBase",
)


def extract_player_character(file_path: Path) -> dict | None:
    """Extract one DCGameplayEffectDataAsset (player class base stats)."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCGameplayEffectDataAsset"), None)
    if not obj:
        return None

    pc_id = obj.get("Name", file_path.stem)
    props = get_properties(obj)

    result: dict = {"id": pc_id}
    for field in _STAT_FIELDS:
        result[camel_to_snake(field)] = props.get(field)

    return result


def run_player_characters(pc_dir: Path, extracted_root: Path) -> dict:
    """Extract all PlayerCharacterEffect files → extracted/classes/<id>.json + _index.json."""
    files = find_files(str(Path(pc_dir) / "Id_PlayerCharacterEffect_*.json"))
    print(f"  [player_characters] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    pcs = {}

    for f in files:
        result = extract_player_character(f)
        if not result:
            continue
        pc_id = result["id"]
        pcs[pc_id] = result
        writer.write_entity("classes", pc_id, result, source_files=[str(f)])
        index_entries.append({
            "id": pc_id,
            "strength_base": result.get("strength_base"),
            "vigor_base": result.get("vigor_base"),
            "move_speed_base": result.get("move_speed_base"),
        })

    writer.write_index("classes", index_entries)
    print(f"  [player_characters] Extracted {len(pcs)} classes")
    return pcs
