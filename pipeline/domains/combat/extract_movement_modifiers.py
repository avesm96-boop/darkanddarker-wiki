"""Extract DCMovementModifierDataAsset → entity files + extracted/combat/movement.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.writer import Writer


def extract_movement_modifier(file_path: Path) -> dict | None:
    """Extract one DCMovementModifierDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCMovementModifierDataAsset"), None)
    if not obj:
        return None

    mm_id = obj.get("Name", file_path.stem)
    props = get_properties(obj)

    return {
        "id": mm_id,
        "multiply": props.get("Multiply"),
        "jump_z_multiply": props.get("JumpZMultiply"),
        "gravity_scale_multiply": props.get("GravityScaleMultiply"),
    }


def run_movement_modifiers(mm_dir: Path, extracted_root: Path) -> dict:
    """Extract all MovementModifier files → entity files + movement.json system file."""
    files = find_files(str(Path(mm_dir) / "Id_MovementModifier_*.json"))
    print(f"  [movement_modifiers] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    modifiers = {}

    for f in files:
        result = extract_movement_modifier(f)
        if not result:
            continue
        mm_id = result["id"]
        modifiers[mm_id] = result
        writer.write_entity("combat", mm_id, result, source_files=[str(f)])
        index_entries.append({"id": mm_id, "multiply": result.get("multiply")})

    writer.write_index("combat", index_entries)

    # Write system file aggregating all modifiers (spec §2.1 canonical movement.json)
    system_data = {
        "modifiers": {
            mm_id: {
                "multiply": v["multiply"],
                "jump_z_multiply": v["jump_z_multiply"],
                "gravity_scale_multiply": v["gravity_scale_multiply"],
            }
            for mm_id, v in modifiers.items()
        }
    }
    writer.write_system("combat", "movement", system_data, source_files=[str(f) for f in files])

    print(f"  [movement_modifiers] Extracted {len(modifiers)} modifiers")
    return modifiers
