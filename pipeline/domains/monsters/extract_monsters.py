"""Extract DCMonsterDataAsset files → extracted/monsters/<id>.json + _index.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_tag, resolve_text
from pipeline.core.writer import Writer


def extract_monster(file_path: Path) -> dict | None:
    """Extract one DCMonsterDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCMonsterDataAsset"), None)
    if not obj:
        return None

    monster_id = obj.get("Name", file_path.stem)
    props = get_properties(obj)

    character_types = [
        resolve_tag(t) for t in (props.get("CharacterTypes") or [])
        if resolve_tag(t) is not None
    ]

    return {
        "id": monster_id,
        "id_tag": resolve_tag(props.get("IdTag")),
        "name": resolve_text(props.get("Name")),
        "class_type": resolve_tag(props.get("ClassType")),
        "grade_type": resolve_tag(props.get("GradeType")),
        "character_types": character_types,
        "adv_point": props.get("AdvPoint"),
        "exp_point": props.get("ExpPoint"),
    }


def run_monsters(monster_dir: Path, extracted_root: Path) -> dict:
    """Extract all Monster files → extracted/monsters/<id>.json + _index.json."""
    files = find_files(str(Path(monster_dir) / "Id_Monster_*.json"))
    print(f"  [monsters] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    monsters = {}

    for f in files:
        result = extract_monster(f)
        if not result:
            continue
        monster_id = result["id"]
        monsters[monster_id] = result
        writer.write_entity("monsters", monster_id, result, source_files=[str(f)])
        index_entries.append({
            "id": monster_id,
            "id_tag": result.get("id_tag"),
            "class_type": result.get("class_type"),
            "grade_type": result.get("grade_type"),
            "adv_point": result.get("adv_point"),
            "exp_point": result.get("exp_point"),
        })

    writer.write_index("monsters", index_entries)
    print(f"  [monsters] Extracted {len(monsters)} monsters")
    return monsters
