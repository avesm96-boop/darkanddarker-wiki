"""Extract DCLootDropRateDataAsset files → extracted/spawns/<id>.json + _index.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files, get_properties
from pipeline.core.writer import Writer


def extract_loot_drop_rate(file_path: Path) -> dict | None:
    """Extract one DCLootDropRateDataAsset file."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCLootDropRateDataAsset"), None)
    if not obj:
        return None

    props = get_properties(obj)
    rates = [
        {
            "luck_grade": item.get("LuckGrade"),
            "drop_rate": item.get("DropRate"),
        }
        for item in (props.get("LootDropRateItemArray") or [])
    ]

    return {
        "id": obj["Name"],
        "rates": rates,
    }


def run_loot_drop_rates(loot_drop_rate_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCLootDropRateDataAsset files."""
    files = find_files(str(Path(loot_drop_rate_dir) / "*.json"))
    print(f"  [loot_drop_rates] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    rates = {}

    for f in files:
        result = extract_loot_drop_rate(f)
        if not result:
            continue
        rate_id = result["id"]
        rates[rate_id] = result
        writer.write_entity("spawns", rate_id, result, source_files=[str(f)])
        index_entries.append({"id": rate_id})

    writer.write_index("spawns", index_entries)
    print(f"  [loot_drop_rates] Extracted {len(rates)} loot drop rates")
    return rates
