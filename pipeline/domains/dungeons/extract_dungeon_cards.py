"""Extract DCDungeonCardDataAsset files → extracted/dungeons/<id>.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files
from pipeline.core.writer import Writer


def extract_dungeon_card(file_path: Path) -> dict | None:
    """Extract one DCDungeonCardDataAsset file. Source data has no Properties."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "DCDungeonCardDataAsset"), None)
    if not obj:
        return None

    return {"id": obj["Name"]}


def run_dungeon_cards(dungeon_card_dir: Path, extracted_root: Path) -> dict:
    """Extract all DCDungeonCardDataAsset files."""
    files = find_files(str(Path(dungeon_card_dir) / "Id_DungeonCard_*.json"))
    print(f"  [dungeon_cards] Found {len(files)} files")

    writer = Writer(extracted_root)
    index_entries = []
    cards = {}

    for f in files:
        result = extract_dungeon_card(f)
        if not result:
            continue
        card_id = result["id"]
        cards[card_id] = result
        writer.write_entity("dungeons", card_id, result, source_files=[str(f)])
        index_entries.append({"id": card_id})

    writer.write_index("dungeons", index_entries)
    print(f"  [dungeon_cards] Extracted {len(cards)} dungeon cards")
    return cards
