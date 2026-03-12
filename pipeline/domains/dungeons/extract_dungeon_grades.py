"""Extract DCDungeonGradeDataAsset files → extracted/dungeons/<id>.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_tag
from pipeline.core.writer import Writer


def extract_dungeon_grade(file_path: Path) -> dict | None:
    """Extract one DCDungeonGradeDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCDungeonGradeDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    return {
        "id": obj["Name"],
        "dungeon_id_tag": resolve_tag(props.get("DungeonIdTag")),
        "gear_pool_index": props.get("GearPoolIndex"),
    }


def run_dungeon_grades(dungeon_grade_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCDungeonGradeDataAsset files."""
    files = find_files(str(Path(dungeon_grade_dir) / "Id_DungeonGrade_*.json"))
    print(f"  [dungeon_grades] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    grades = {}

    for f in files:
        result = extract_dungeon_grade(f)
        if not result:
            continue
        grade_id = result["id"]
        grades[grade_id] = result
        writer.write_entity("dungeons", grade_id, result, source_files=[str(f)])
        index_entries.append({"id": grade_id})

    writer.write_index("dungeons", index_entries)
    print(f"  [dungeon_grades] Extracted {len(grades)} dungeon grades")
    return grades
