"""Extract DCProjectileDataAsset files → extracted/combat/<id>.json + _index.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_tag
from pipeline.core.writer import Writer


def extract_projectile(file_path: Path) -> dict | None:
    """Extract one DCProjectileDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCProjectileDataAsset"), None)
    if not obj:
        return None

    proj_id = obj.get("Name", file_path.stem)
    props = get_properties(obj)

    source_types = [
        resolve_tag(t) for t in (props.get("SourceTypes") or [])
        if resolve_tag(t) is not None
    ]

    return {
        "id": proj_id,
        "source_types": source_types,
    }


def run_projectiles(projectile_dir: Path, extracted_root: Path) -> dict:
    """Extract all Projectile files → extracted/combat/<id>.json + _index.json.

    NOTE: The Projectile V2 directory also contains DCGameplayAbilityDataAsset and
    DCGameplayEffectDataAsset files. extract_projectile() skips them via type filter.
    """
    files = find_files(str(Path(projectile_dir) / "**" / "*.json"))
    print(f"  [projectiles] Found {len(files)} files (will skip non-DCProjectileDataAsset)")

    writer = Writer(extracted_root)
    index_entries = []
    projectiles = {}

    for f in files:
        result = extract_projectile(f)
        if not result:
            continue
        proj_id = result["id"]
        projectiles[proj_id] = result
        writer.write_entity("combat", proj_id, result, source_files=[str(f)])
        index_entries.append({
            "id": proj_id,
            "source_types": result.get("source_types"),
        })

    writer.write_index("combat", index_entries)
    print(f"  [projectiles] Extracted {len(projectiles)} projectiles")
    return projectiles
