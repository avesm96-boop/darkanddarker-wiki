"""Extract ItemPropertyType catalog and ItemProperty instance lookup.

extract_item_property_type(): parses one DCItemPropertyTypeDataAsset file.
build_property_lookup(): returns {item_id: [entries]} from all ItemProperty files.
run_item_property_types(): writes extracted/items/item_property_types.json.
"""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.normalizer import resolve_tag, resolve_ref
from pipeline.core.writer import Writer


def extract_item_property_type(file_path: Path) -> dict | None:
    """Extract one DCItemPropertyTypeDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCItemPropertyTypeDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    return {
        "id": obj.get("Name", file_path.stem),
        "property_type": resolve_tag(props.get("PropertyType")),
        "value_ratio": props.get("ValueRatio", 1.0),
        "enchant_item_id": resolve_tag(props.get("EnchantItemIdTag")),
        "source_file": str(file_path),
    }


def _resolve_property_type_id(value) -> str | None:
    """Resolve PropertyTypeId — may be a tag or an asset ref (AssetPathName)."""
    if value is None:
        return None
    # Try TagName first
    tag = resolve_tag(value)
    if tag is not None:
        return tag
    # Try standard ObjectName/ObjectPath ref
    ref = resolve_ref(value)
    if ref is not None:
        return ref
    # Handle AssetPathName format: extract the stem of the asset path
    if isinstance(value, dict) and "AssetPathName" in value:
        asset_path = value["AssetPathName"]
        # e.g. '/Game/.../Id_ItemPropertyType_Effect_ArmorRating.Id_ItemPropertyType_Effect_ArmorRating'
        # Take the part after the last '/' and before the first '.'
        stem = asset_path.rsplit("/", 1)[-1].split(".")[0]
        return stem if stem else None
    return None


def build_property_lookup(property_dir: Path) -> dict:
    """Build {item_id: [property_entries]} from ItemProperty files.

    Links Id_ItemProperty_Primary_<Suffix> → Id_Item_<Suffix>.
    Does NOT write any output files.
    """
    lookup: dict[str, list] = {}
    prefixes = ("Id_ItemProperty_Primary_", "Id_ItemProperty_Secondary_", "Id_ItemProperty_")

    for f in find_files(str(Path(property_dir) / "Id_ItemProperty_*.json")):
        try:
            data = load(f)
        except (FileNotFoundError, ValueError):
            continue

        obj = next((o for o in data if isinstance(o, dict)
                    and o.get("Type") == "DCItemPropertyDataAsset"), None)
        if not obj:
            continue

        # Derive item_id from file stem
        stem = f.stem
        item_id = None
        for prefix in prefixes:
            if stem.startswith(prefix):
                item_id = "Id_Item_" + stem[len(prefix):]
                break
        if not item_id:
            continue

        props = get_properties(obj)
        entries = []
        for entry in (props.get("ItemPropertyItemArray") or []):
            entries.append({
                "property_type": _resolve_property_type_id(entry.get("PropertyTypeId")),
                "min_value": entry.get("MinValue"),
                "max_value": entry.get("MaxValue"),
                "enchant_min_value": entry.get("EnchantMinValue"),
                "enchant_max_value": entry.get("EnchantMaxValue"),
            })

        if entries:
            lookup.setdefault(item_id, []).extend(entries)

    return lookup


def run_item_property_types(type_dir: Path, extracted_root: Path) -> dict:
    """Extract all ItemPropertyType files → extracted/items/item_property_types.json."""
    files = find_files(str(Path(type_dir) / "Id_ItemPropertyType_*.json"))
    print(f"  [item_property_types] Found {len(files)} files")

    types = {}
    source_files = []
    for f in files:
        result = extract_item_property_type(f)
        if result:
            types[result["id"]] = {
                "property_type": result["property_type"],
                "value_ratio": result["value_ratio"],
                "enchant_item_id": result["enchant_item_id"],
            }
            source_files.append(result["source_file"])

    writer = Writer(extracted_root)
    writer.write_system("items", "item_property_types", {"types": types},
                        source_files=source_files)
    print(f"  [item_property_types] Extracted {len(types)} property types")
    return types
