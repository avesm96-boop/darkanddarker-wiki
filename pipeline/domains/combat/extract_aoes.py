"""Extract DCAoeDataAsset files → extracted/combat/<id>.json + _index.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.writer import Writer


def _extract_asset_id(ref: dict) -> str | None:
    """Extract asset ID from {"AssetPathName": "/Game/.../Foo.Foo", "SubPathString": ""}."""
    if not isinstance(ref, dict):
        return None
    asset_path = ref.get("AssetPathName", "")
    if not asset_path:
        return None
    # AssetPathName format: "/Game/Path/To/AssetName.AssetName"
    # We want the last component after the final dot
    parts = asset_path.split(".")
    if len(parts) > 0:
        return parts[-1]
    return None


def extract_aoe(file_path: Path) -> dict | None:
    """Extract one DCAoeDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCAoeDataAsset"), None)
    if not obj:
        return None

    aoe_id = obj.get("Name", file_path.stem)
    props = get_properties(obj)

    abilities = [
        _extract_asset_id(a) for a in (props.get("Abilities") or [])
        if _extract_asset_id(a) is not None
    ]

    return {
        "id": aoe_id,
        "art_data": _extract_asset_id(props.get("ArtData")),
        "sound_data": _extract_asset_id(props.get("SoundData")),
        "abilities": abilities,
    }


def run_aoes(aoe_dir: Path, extracted_root: Path) -> dict:
    """Extract all Aoe files → extracted/combat/<id>.json + _index.json.

    NOTE: The Aoe V2 directory also contains DCGameplayAbilityDataAsset files.
    extract_aoe() skips them via type filter.
    """
    files = find_files(str(Path(aoe_dir) / "Id_Aoe_*.json"))
    print(f"  [aoes] Found {len(files)} files (will skip non-DCAoeDataAsset)")

    writer = Writer(extracted_root)
    index_entries = []
    aoes = {}

    for f in files:
        result = extract_aoe(f)
        if not result:
            continue
        aoe_id = result["id"]
        aoes[aoe_id] = result
        writer.write_entity("combat", aoe_id, result, source_files=[str(f)])
        index_entries.append({"id": aoe_id})

    writer.write_index("combat", index_entries)
    print(f"  [aoes] Extracted {len(aoes)} AOEs")
    return aoes
