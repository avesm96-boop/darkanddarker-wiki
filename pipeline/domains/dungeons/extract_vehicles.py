"""Extract vehicle assets → extracted/dungeons/<id>.json.

Handles three types in Vehicle/ sub-directory:
  DCVehicleDataAsset          → Vehicle/Vehicle/
  DCGameplayEffectDataAsset   → Vehicle/VehicleEffect/
  DCPropsInteractDataAsset    → Vehicle/VehicleInteract/

Skips Vehicle/VehicleAbility/ (DCGameplayAbilityDataAsset).
"""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_tag, resolve_text
from pipeline.core.writer import Writer


def _extract_asset_id(ref: dict) -> str | None:
    """Extract asset ID from {"AssetPathName": "/Game/.../Foo.Foo", "SubPathString": ""}."""
    if not isinstance(ref, dict):
        return None
    asset_path = ref.get("AssetPathName", "")
    if not asset_path:
        return None
    parts = asset_path.split(".")
    return parts[-1] if len(parts) > 1 else None


def extract_vehicle(file_path: Path) -> dict | None:
    """Extract one DCVehicleDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCVehicleDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    return {
        "id": obj["Name"],
        "id_tag": resolve_tag(props.get("IdTag")),
        "name": resolve_text(props.get("Name")),
        "swimming_movement_modifier": _extract_asset_id(props.get("SwimmingMovementModifier")),
    }


def extract_vehicle_effect(file_path: Path) -> dict | None:
    """Extract one DCGameplayEffectDataAsset file from Vehicle/VehicleEffect/."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCGameplayEffectDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    return {
        "id": obj["Name"],
        "strength_base": props.get("StrengthBase"),
        "vigor_base": props.get("VigorBase"),
        "agility_base": props.get("AgilityBase"),
        "dexterity_base": props.get("DexterityBase"),
        "will_base": props.get("WillBase"),
        "knowledge_base": props.get("KnowledgeBase"),
        "resourcefulness_base": props.get("ResourcefulnessBase"),
        "impact_resistance": props.get("ImpactResistance"),
        "move_speed_base": props.get("MoveSpeedBase"),
    }


def extract_vehicle_interact(file_path: Path) -> dict | None:
    """Extract one DCPropsInteractDataAsset file from Vehicle/VehicleInteract/."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCPropsInteractDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    return {
        "id": obj["Name"],
        "interaction_name": resolve_text(props.get("InteractionName")),
        "interaction_text": resolve_text(props.get("InteractionText")),
        "duration": props.get("Duration"),
        "interactable_tag": resolve_tag(props.get("InteractableTag")),
        "trigger_tag": resolve_tag(props.get("TriggerTag")),
        "ability_trigger_tag": resolve_tag(props.get("AbilityTriggerTag")),
    }


def run_vehicles(vehicle_dir: Path, extracted_root: Path) -> dict:
    """Extract all vehicle assets from sub-directories.

    Scans Vehicle/, VehicleEffect/, VehicleInteract/ under vehicle_dir.
    Skips VehicleAbility/ (DCGameplayAbilityDataAsset).
    Tags each entity with _entity_type. Returns combined {id: entity} dict.
    """
    vehicle_dir = Path(vehicle_dir)
    writer = Writer(extracted_root)
    all_vehicles = {}

    extractors = [
        ("Vehicle", extract_vehicle, "vehicle"),
        ("VehicleEffect", extract_vehicle_effect, "vehicle_effect"),
        ("VehicleInteract", extract_vehicle_interact, "vehicle_interact"),
    ]

    for subdir, extractor, entity_type in extractors:
        subdir_path = vehicle_dir / subdir
        if not subdir_path.exists():
            print(f"  [vehicles] WARNING: {subdir_path} not found")
            continue
        files = find_files(str(subdir_path / "*.json"))
        print(f"  [vehicles/{subdir}] Found {len(files)} files")
        for f in files:
            result = extractor(f)
            if not result:
                continue
            vid = result["id"]
            tagged = {**result, "_entity_type": entity_type}
            all_vehicles[vid] = tagged
            writer.write_entity("dungeons", vid, result, source_files=[str(f)])

    writer.write_index("dungeons", [{"id": v["id"]} for v in all_vehicles.values()])
    print(f"  [vehicles] Extracted {len(all_vehicles)} vehicle entities total")
    return all_vehicles
