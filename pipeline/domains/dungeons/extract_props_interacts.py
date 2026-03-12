"""Extract DCPropsInteractDataAsset files → extracted/dungeons/<id>.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_tag, resolve_text
from pipeline.core.writer import Writer


def extract_props_interact(file_path: Path) -> dict | None:
    """Extract one DCPropsInteractDataAsset file."""
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


def run_props_interacts(props_interact_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCPropsInteractDataAsset files."""
    files = find_files(str(Path(props_interact_dir) / "*.json"))
    print(f"  [props_interacts] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    interacts = {}

    for f in files:
        result = extract_props_interact(f)
        if not result:
            continue
        interact_id = result["id"]
        interacts[interact_id] = result
        writer.write_entity("dungeons", interact_id, result, source_files=[str(f)])
        index_entries.append({"id": interact_id})

    writer.write_index("dungeons", index_entries)
    print(f"  [props_interacts] Extracted {len(interacts)} props interacts")
    return interacts
