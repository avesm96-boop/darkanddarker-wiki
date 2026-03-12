"""Extract DCMeleeAttackDataAsset files → extracted/combat/<id>.json + _index.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_tag
from pipeline.core.writer import Writer


def extract_melee_attack(file_path: Path) -> dict | None:
    """Extract one DCMeleeAttackDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCMeleeAttackDataAsset"), None)
    if not obj:
        return None

    attack_id = obj.get("Name", file_path.stem)
    props = get_properties(obj)

    return {
        "id": attack_id,
        "hit_play_rate": props.get("HitPlayRate"),
        "hit_play_rate_duration": props.get("HitPlayRateDuration"),
        "combo_type_tag": resolve_tag(props.get("ComboTypeTag")),
        "can_stuck_by_static_object": props.get("CanStuckByStaticObject", False),
        "weak_shield_stuck_play_rate_duration": props.get("WeakShieldStuckPlayRateDuration"),
        "static_object_stuck_play_rate": props.get("StaticObjectStuckPlayRate"),
        "static_object_stuck_play_rate_duration": props.get("StaticObjectStuckPlayRateDuration"),
    }


def run_melee_attacks(melee_dir: Path, extracted_root: Path) -> dict:
    """Extract all MeleeAttack files → extracted/combat/<id>.json + _index.json."""
    files = find_files(str(Path(melee_dir) / "Id_MeleeAttack_*.json"))
    print(f"  [melee_attacks] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    attacks = {}

    for f in files:
        result = extract_melee_attack(f)
        if not result:
            continue
        attack_id = result["id"]
        attacks[attack_id] = result
        writer.write_entity("combat", attack_id, result, source_files=[str(f)])
        index_entries.append({
            "id": attack_id,
            "combo_type_tag": result.get("combo_type_tag"),
        })

    writer.write_index("combat", index_entries)
    print(f"  [melee_attacks] Extracted {len(attacks)} melee attacks")
    return attacks
