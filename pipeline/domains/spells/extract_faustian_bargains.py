"""Extract DCFaustianBargainDataAsset → extracted/spells/<id>.json + _index.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.writer import Writer


def _resolve_asset_path_name(value: dict | None) -> str | None:
    """Resolve {AssetPathName: '/Game/.../Id_Foo.Id_Foo'} → 'Id_Foo'."""
    if not isinstance(value, dict):
        return None
    path = value.get("AssetPathName", "")
    if not path or path == "None":
        return None
    return path.split("/")[-1].split(".")[0]


def _resolve_asset_list(items: list) -> list[str]:
    """Resolve a list of AssetPathName dicts → list of ID strings."""
    result = []
    for item in (items or []):
        resolved = _resolve_asset_path_name(item)
        if resolved:
            result.append(resolved)
    return result


def extract_faustian_bargain(file_path: Path) -> dict | None:
    """Extract one DCFaustianBargainDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCFaustianBargainDataAsset"), None)
    if not obj:
        return None

    fb_id = obj.get("Name", file_path.stem)
    props = get_properties(obj)

    return {
        "id": fb_id,
        "monster_id": _resolve_asset_path_name(props.get("MonsterId")),
        "required_affinity": props.get("RequiredAffinity"),
        "skills": _resolve_asset_list(props.get("Skills")),
        "abilities": _resolve_asset_list(props.get("Abilities")),
        "effects": _resolve_asset_list(props.get("Effects")),
    }


def run_faustian_bargains(fb_dir: Path, extracted_root: Path) -> dict:
    """Extract all FaustianBargain files → extracted/spells/<id>.json + _index.json."""
    files = find_files(str(Path(fb_dir) / "Id_FaustianBargain_*.json"))
    print(f"  [faustian_bargains] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    bargains = {}

    for f in files:
        result = extract_faustian_bargain(f)
        if not result:
            continue
        fb_id = result["id"]
        bargains[fb_id] = result
        writer.write_entity("spells", fb_id, result, source_files=[str(f)])
        index_entries.append({
            "id": fb_id,
            "monster_id": result.get("monster_id"),
            "required_affinity": result.get("required_affinity"),
        })

    writer.write_index("spells", index_entries)
    print(f"  [faustian_bargains] Extracted {len(bargains)} Faustian bargains")
    return bargains
