"""Extract DCSkillDataAsset files → extracted/classes/<id>.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_text, resolve_tag
from pipeline.core.writer import Writer


def _extract_class_ids(classes_list: list) -> list[str]:
    """Extract PrimaryAssetName strings from the Classes array."""
    result = []
    for entry in (classes_list or []):
        if isinstance(entry, dict):
            name = entry.get("PrimaryAssetName")
            if name:
                result.append(name)
    return result


def extract_skill(file_path: Path) -> dict | None:
    """Extract one DCSkillDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCSkillDataAsset"), None)
    if not obj:
        return None

    skill_id = obj.get("Name", file_path.stem)
    props = get_properties(obj)

    return {
        "id": skill_id,
        "name": resolve_text(props.get("Name")),
        "description": resolve_text(props.get("DescData")),
        "skill_type": resolve_tag(props.get("SkillType")),
        "skill_tier": props.get("SkillTier"),
        "use_moving": props.get("UseMoving", False),
        "classes": _extract_class_ids(props.get("Classes")),
    }


def run_skills(skill_dir: Path, extracted_root: Path) -> dict:
    """Extract all Skill files → extracted/classes/<id>.json."""
    files = find_files(str(Path(skill_dir) / "Id_Skill_*.json"))
    print(f"  [skills] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    skills = {}

    for f in files:
        result = extract_skill(f)
        if not result:
            continue
        skill_id = result["id"]
        skills[skill_id] = result
        writer.write_entity("classes", skill_id, result, source_files=[str(f)])
        index_entries.append({
            "id": skill_id,
            "name": result.get("name"),
            "skill_type": result.get("skill_type"),
            "skill_tier": result.get("skill_tier"),
            "classes": result.get("classes"),
        })

    writer.write_index("classes", index_entries)
    print(f"  [skills] Extracted {len(skills)} skills")
    return skills
