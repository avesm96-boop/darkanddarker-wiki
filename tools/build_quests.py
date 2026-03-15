"""
build_quests.py - Compile all quest data into website/public/data/quests.json

Reads from:
  - raw/.../V2/Quest/Quest/              — quest definitions (level, prereqs)
  - raw/.../V2/Quest/QuestChapter/       — chapter groupings & display names
  - raw/.../V2/Quest/QuestContentKill/   — kill objectives
  - raw/.../V2/Quest/QuestContentFetch/  — fetch/gather objectives
  - raw/.../V2/Quest/QuestContentEscape/ — escape objectives
  - raw/.../V2/Quest/QuestContentExplore/— explore objectives
  - raw/.../V2/Quest/QuestContentDamage/ — damage objectives
  - raw/.../V2/Quest/QuestContentHold/   — hold objectives
  - raw/.../V2/Quest/QuestContentProps/  — props/destroy objectives
  - raw/.../V2/Quest/QuestContentUseItem/— use-item objectives
  - raw/.../V2/Quest/QuestReward/        — reward definitions
  - raw/.../V2/Merchant/Merchant/        — merchant names

Outputs:
  - website/public/data/quests.json

Usage:
    py -3 tools/build_quests.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_BASE = ROOT / "raw" / "DungeonCrawler" / "Content" / "DungeonCrawler" / "Data" / "Generated" / "V2"
RAW_QUEST = RAW_BASE / "Quest"
RAW_MERCHANT = RAW_BASE / "Merchant" / "Merchant"
OUTPUT_FILE = ROOT / "website" / "public" / "data" / "quests.json"

# Directories for quest content types
CONTENT_DIRS = {
    "kill":    RAW_QUEST / "QuestContentKill",
    "fetch":   RAW_QUEST / "QuestContentFetch",
    "escape":  RAW_QUEST / "QuestContentEscape",
    "explore": RAW_QUEST / "QuestContentExplore",
    "damage":  RAW_QUEST / "QuestContentDamage",
    "hold":    RAW_QUEST / "QuestContentHold",
    "props":   RAW_QUEST / "QuestContentProps",
    "useitem": RAW_QUEST / "QuestContentUseItem",
}

# Friendly merchant names (fallback if not found in raw data)
MERCHANT_DISPLAY_NAMES = {
    "Alchemist": "The Alchemist",
    "Armourer": "The Armourer",
    "Cockatrice": "Cockatrice",
    "Dealmaker": "The Dealmaker",
    "Expressman": "The Expressman",
    "FortuneTeller": "The Fortune Teller",
    "GoblinMerchant": "Goblin Merchant",
    "Goldsmith": "The Goldsmith",
    "Huntress": "The Huntress",
    "JackOLantern": "Jack O'Lantern",
    "Krampus": "Krampus",
    "Leathersmith": "The Leathersmith",
    "Miner": "The Miner",
    "Navigator": "The Navigator",
    "Nicholas": "Nicholas",
    "NightmareMummy": "Nightmare Mummy",
    "PumpkinMan": "Pumpkin Man",
    "SkeletonFootman": "Skeleton Footman",
    "Squire": "The Squire",
    "Surgeon": "The Surgeon",
    "Tailor": "The Tailor",
    "TavernMaster": "The Tavern Master",
    "TheCollector": "The Collector",
    "Treasurer": "The Treasurer",
    "Valentine": "Valentine",
    "Weaponsmith": "The Weaponsmith",
    "Woodsman": "The Woodsman",
}

# Dungeon tag to friendly name
DUNGEON_TAG_NAMES = {
    "Id.Dungeon.Crypts": "Forgotten Crypt",
    "Id.Dungeon.Goblin": "Goblin Cave",
    "Id.Dungeon.IceCavern": "Ice Cavern",
    "Id.Dungeon.IceAbyss": "Ice Abyss",
    "Id.Dungeon.Inferno": "Inferno",
    "Id.Dungeon.Ruins": "Ruins",
    "Id.Dungeon.ShipGraveyard": "Ship Graveyard",
    "Id.Dungeon.Firedeep": "Firedeep",
    "Id.Dungeon.ForgottenCastle": "Forgotten Castle",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_fmodel_json(path: Path) -> dict | None:
    """Load an FModel-exported JSON and return the first object's Properties."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list) and data:
            return data[0]
        return None
    except (json.JSONDecodeError, FileNotFoundError, IndexError) as e:
        print(f"  WARNING: Failed to load {path}: {e}", file=sys.stderr)
        return None


def extract_asset_id(ref: dict | None) -> str | None:
    """Extract the asset ID from an AssetPathName reference."""
    if not isinstance(ref, dict):
        return None
    path = ref.get("AssetPathName", "")
    if not path:
        return None
    parts = path.split(".")
    return parts[-1] if len(parts) > 1 else None


def extract_tag_name(tag: dict | None) -> str | None:
    """Extract TagName from a tag dict."""
    if isinstance(tag, dict):
        return tag.get("TagName")
    return None


def extract_dungeon_tags(props: dict) -> list[str]:
    """Extract dungeon tags from DungeonIdTags array."""
    tags = props.get("DungeonIdTags", [])
    result = []
    for t in tags:
        name = extract_tag_name(t)
        if name:
            result.append(name)
    return result


def dungeon_tag_to_name(tag: str) -> str:
    """Convert a dungeon tag to a friendly name."""
    return DUNGEON_TAG_NAMES.get(tag, tag.replace("Id.Dungeon.", ""))


def extract_text_field(text_obj: dict | None) -> str | None:
    """Extract the text key or localized string from an FModel text object."""
    if not isinstance(text_obj, dict):
        return None
    # Prefer Key (localization key), fall back to LocalizedString
    return text_obj.get("Key") or text_obj.get("LocalizedString") or text_obj.get("SourceString")


def item_id_to_name(item_id: str) -> str:
    """Convert Id_Item_BlackRose -> Black Rose, handling CamelCase."""
    # Strip Id_Item_ prefix
    name = item_id
    if name.startswith("Id_Item_"):
        name = name[8:]
    # Insert spaces before capital letters (CamelCase -> Camel Case)
    name = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name)
    name = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", name)
    # Replace underscores with spaces
    name = name.replace("_", " ")
    return name.strip()


def tag_to_name(tag: str, prefix: str) -> str:
    """Convert Id.Monster.Abomination -> Abomination, etc."""
    if tag.startswith(prefix):
        name = tag[len(prefix):]
    else:
        name = tag
    # Insert spaces before capitals
    name = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name)
    return name.strip()


def module_path_to_name(asset_path: str) -> str:
    """Extract a readable module name from an asset path."""
    # /Game/.../Id_DungeonModule_Ruins_GreatHall_03_Destroyed.Id_DungeonModule...
    asset_id = asset_path.split(".")[-1] if "." in asset_path else asset_path
    # Strip prefix
    name = asset_id
    if name.startswith("Id_DungeonModule_"):
        name = name[17:]
    # Replace underscores, insert spaces
    name = name.replace("_", " ")
    return name.strip()


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_all_quest_content() -> dict[str, dict]:
    """Load all quest content (objectives) from all content subdirectories."""
    content_by_id: dict[str, dict] = {}

    for content_type, directory in CONTENT_DIRS.items():
        if not directory.is_dir():
            print(f"  WARNING: Content directory not found: {directory}", file=sys.stderr)
            continue

        for file_path in sorted(directory.glob("*.json")):
            obj = load_fmodel_json(file_path)
            if not obj:
                continue

            content_id = obj.get("Name", file_path.stem)
            props = obj.get("Properties", {})
            parsed = {"type": content_type, "id": content_id}

            count = props.get("ContentCount")
            if count is not None:
                parsed["count"] = count

            # Dungeon tags (common across types)
            dungeons = extract_dungeon_tags(props)
            if dungeons:
                parsed["dungeons"] = [dungeon_tag_to_name(d) for d in dungeons]

            # Type-specific fields
            if content_type == "kill":
                kill_tag = extract_tag_name(props.get("KillTag"))
                if kill_tag:
                    parsed["target"] = tag_to_name(kill_tag, "Id.Monster.")
                    parsed["target_tag"] = kill_tag
                kill_type = props.get("KillType", "")
                if kill_type:
                    parsed["kill_type"] = kill_type.split("::")[-1]
                if props.get("SingleSession"):
                    parsed["single_session"] = True

            elif content_type == "fetch":
                item_tag = extract_tag_name(props.get("ItemIdTag"))
                if item_tag:
                    item_id = item_tag.replace("Id.Item.", "")
                    parsed["item"] = item_id
                    parsed["item_name"] = tag_to_name(item_tag, "Id.Item.")
                # Some fetch quests use TypeTag + RarityType instead of specific item
                type_tag = extract_tag_name(props.get("TypeTag"))
                if type_tag:
                    parsed["item_type"] = tag_to_name(type_tag, "Type.Item.")
                rarity_tag = extract_tag_name(props.get("RarityType"))
                if rarity_tag:
                    parsed["rarity"] = tag_to_name(rarity_tag, "Type.Item.Rarity.")
                loot_state = props.get("ItemLootState", "")
                if loot_state:
                    parsed["loot_state"] = loot_state.split("::")[-1]

            elif content_type == "escape":
                if props.get("ConsecutiveEscape"):
                    parsed["consecutive"] = True

            elif content_type == "explore":
                module_ref = props.get("ModuleId")
                if isinstance(module_ref, dict):
                    asset_path = module_ref.get("AssetPathName", "")
                    if asset_path:
                        parsed["module"] = module_path_to_name(asset_path)

            elif content_type == "damage":
                damage_type = props.get("DamageType", "")
                if damage_type:
                    parsed["damage_type"] = damage_type.split("::")[-1]
                tag_queries = props.get("TagQueryData", [])
                if tag_queries:
                    parsed["conditions"] = [
                        extract_asset_id(t) or "" for t in tag_queries if isinstance(t, dict)
                    ]

            elif content_type == "hold":
                module_ref = props.get("ModuleId")
                if isinstance(module_ref, dict):
                    asset_path = module_ref.get("AssetPathName", "")
                    if asset_path:
                        parsed["module"] = module_path_to_name(asset_path)
                hold_time = props.get("HoldTime")
                if hold_time is not None:
                    parsed["hold_time"] = hold_time
                if props.get("SingleSession"):
                    parsed["single_session"] = True
                if props.get("MustEscape"):
                    parsed["must_escape"] = True

            elif content_type == "props":
                props_tag = extract_tag_name(props.get("PropsIdTag"))
                if props_tag:
                    parsed["props_target"] = tag_to_name(props_tag, "Id.Props.")
                    parsed["props_tag"] = props_tag
                props_type = props.get("PropsType", "")
                if props_type:
                    parsed["action"] = props_type.split("::")[-1]

            elif content_type == "useitem":
                item_tag = extract_tag_name(props.get("ItemIdTag"))
                if item_tag:
                    item_id = item_tag.replace("Id.Item.", "")
                    parsed["item"] = item_id
                    parsed["item_name"] = tag_to_name(item_tag, "Id.Item.")
                item_type = props.get("ItemType", "")
                if item_type:
                    parsed["item_type"] = item_type.split("::")[-1]

            content_by_id[content_id] = parsed

    return content_by_id


def load_all_rewards() -> dict[str, list[dict]]:
    """Load all quest rewards, keyed by reward ID."""
    reward_dir = RAW_QUEST / "QuestReward"
    rewards_by_id: dict[str, list[dict]] = {}

    if not reward_dir.is_dir():
        print(f"  WARNING: Reward directory not found: {reward_dir}", file=sys.stderr)
        return rewards_by_id

    for file_path in sorted(reward_dir.glob("*.json")):
        obj = load_fmodel_json(file_path)
        if not obj:
            continue

        reward_id = obj.get("Name", file_path.stem)
        props = obj.get("Properties", {})
        reward_items = props.get("RewardItemArray", [])

        parsed_rewards = []
        for item in reward_items:
            reward_type = item.get("RewardType", "").split("::")[-1]
            reward_rid = item.get("RewardId", "")
            reward_count = item.get("RewardCount", 0)

            entry: dict = {"type": reward_type.lower()}

            if reward_type == "Item":
                entry["id"] = reward_rid
                entry["name"] = item_id_to_name(reward_rid)
                entry["count"] = reward_count
            elif reward_type == "Exp":
                entry["count"] = reward_count
            elif reward_type == "Affinity":
                # RewardId is like "Id_Merchant_Alchemist"
                merchant_key = reward_rid.replace("Id_Merchant_", "") if reward_rid.startswith("Id_Merchant_") else reward_rid
                entry["merchant"] = merchant_key
                entry["count"] = reward_count
            else:
                entry["id"] = reward_rid
                entry["count"] = reward_count

            parsed_rewards.append(entry)

        rewards_by_id[reward_id] = parsed_rewards

    return rewards_by_id


def load_all_chapters() -> list[dict]:
    """Load quest chapters for grouping."""
    chapter_dir = RAW_QUEST / "QuestChapter"
    chapters = []

    if not chapter_dir.is_dir():
        print(f"  WARNING: Chapter directory not found: {chapter_dir}", file=sys.stderr)
        return chapters

    for file_path in sorted(chapter_dir.glob("*.json")):
        obj = load_fmodel_json(file_path)
        if not obj:
            continue

        props = obj.get("Properties", {})
        quest_refs = props.get("Quests", [])
        quest_ids = [extract_asset_id(q) for q in quest_refs if isinstance(q, dict)]
        quest_ids = [q for q in quest_ids if q]

        name_data = props.get("Name")
        chapter_name = extract_text_field(name_data) if isinstance(name_data, dict) else None
        localized = name_data.get("LocalizedString", "") if isinstance(name_data, dict) else ""

        chapters.append({
            "id": obj.get("Name", file_path.stem),
            "name_key": chapter_name,
            "name": localized if localized and localized != chapter_name else None,
            "order": props.get("Order"),
            "quest_ids": quest_ids,
        })

    chapters.sort(key=lambda c: c.get("order") or 0)
    return chapters


def load_all_quests() -> dict[str, dict]:
    """Load all raw quest definitions."""
    quest_dir = RAW_QUEST / "Quest"
    quests: dict[str, dict] = {}

    if not quest_dir.is_dir():
        print(f"  ERROR: Quest directory not found: {quest_dir}", file=sys.stderr)
        return quests

    for file_path in sorted(quest_dir.glob("*.json")):
        obj = load_fmodel_json(file_path)
        if not obj:
            continue

        quest_id = obj.get("Name", file_path.stem)
        props = obj.get("Properties", {})

        quest: dict = {"id": quest_id}

        # Title text
        title_text = extract_text_field(props.get("TitleText"))
        if title_text:
            quest["title"] = title_text
        title_localized = props.get("TitleText", {}).get("LocalizedString", "") if isinstance(props.get("TitleText"), dict) else ""
        if title_localized and title_localized != title_text:
            quest["title_localized"] = title_localized

        # Required level
        req_level = props.get("RequiredLevel")
        if req_level is not None:
            quest["required_level"] = req_level

        # Required quest
        req_quest = extract_asset_id(props.get("RequiredQuest"))
        if req_quest:
            quest["required_quest"] = req_quest

        # Explicit quest contents (only some quests have this)
        content_refs = props.get("QuestContents", [])
        explicit_content_ids = [extract_asset_id(c) for c in content_refs if isinstance(c, dict)]
        explicit_content_ids = [c for c in explicit_content_ids if c]
        if explicit_content_ids:
            quest["_content_ids"] = explicit_content_ids

        # Explicit reward reference
        reward_ref = extract_asset_id(props.get("QuestReward"))
        if reward_ref:
            quest["_reward_id"] = reward_ref

        quests[quest_id] = quest

    return quests


def load_merchant_names() -> dict[str, str]:
    """Load merchant display names from raw data."""
    names: dict[str, str] = {}

    if not RAW_MERCHANT.is_dir():
        return names

    for file_path in sorted(RAW_MERCHANT.glob("*.json")):
        obj = load_fmodel_json(file_path)
        if not obj:
            continue

        merchant_id = obj.get("Name", "")
        key = merchant_id.replace("Id_Merchant_", "") if merchant_id.startswith("Id_Merchant_") else merchant_id

        props = obj.get("Properties", {})
        name_data = props.get("Name")
        localized = name_data.get("LocalizedString", "") if isinstance(name_data, dict) else ""

        if localized and not localized.startswith("Text_"):
            names[key] = localized

    return names


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------

def extract_merchant_from_quest_id(quest_id: str) -> str | None:
    """Extract merchant name from quest ID: Id_Quest_{Merchant}_{rest}."""
    m = re.match(r"Id_Quest_([A-Za-z]+)_", quest_id)
    return m.group(1) if m else None


def build_quest_entry(
    quest: dict,
    content_by_id: dict[str, dict],
    rewards_by_id: dict[str, list[dict]],
) -> dict:
    """Build a fully resolved quest entry."""
    quest_id = quest["id"]
    entry: dict = {"id": quest_id}

    if "title" in quest:
        entry["title"] = quest["title"]
    if "title_localized" in quest:
        entry["title_localized"] = quest["title_localized"]
    if "required_level" in quest:
        entry["required_level"] = quest["required_level"]
    if "required_quest" in quest:
        entry["required_quest"] = quest["required_quest"]

    # Resolve objectives
    content_ids = quest.get("_content_ids", [])
    if content_ids:
        objectives = []
        for cid in content_ids:
            if cid in content_by_id:
                obj = dict(content_by_id[cid])
                obj.pop("id", None)  # Remove the raw content ID from output
                objectives.append(obj)
            else:
                objectives.append({"type": "unknown", "content_id": cid})
        entry["objectives"] = objectives

    # Resolve rewards
    reward_id = quest.get("_reward_id")
    if not reward_id:
        # Fall back to naming convention: Id_Quest_X_NN -> Id_Reward_Quest_X_NN
        reward_id = quest_id.replace("Id_Quest_", "Id_Reward_Quest_")

    if reward_id in rewards_by_id:
        entry["rewards"] = rewards_by_id[reward_id]
        entry["_reward_id"] = reward_id
    elif quest.get("_reward_id"):
        # Had explicit ref but no data found
        entry["_reward_id"] = quest["_reward_id"]

    return entry


def build():
    print("[build_quests] Loading quest content (objectives)...")
    content_by_id = load_all_quest_content()
    print(f"  Loaded {len(content_by_id)} quest content entries")

    print("[build_quests] Loading quest rewards...")
    rewards_by_id = load_all_rewards()
    print(f"  Loaded {len(rewards_by_id)} reward entries")

    print("[build_quests] Loading quest chapters...")
    chapters = load_all_chapters()
    print(f"  Loaded {len(chapters)} chapters")

    print("[build_quests] Loading quests...")
    quests = load_all_quests()
    print(f"  Loaded {len(quests)} quests")

    print("[build_quests] Loading merchant names...")
    merchant_names_raw = load_merchant_names()
    print(f"  Loaded {len(merchant_names_raw)} merchant names from raw data")

    # Build quest-to-chapter mapping
    quest_to_chapter: dict[str, dict] = {}
    for ch in chapters:
        for qid in ch["quest_ids"]:
            quest_to_chapter[qid] = ch

    # Group quests by merchant
    merchant_quests: dict[str, list[dict]] = defaultdict(list)
    no_merchant = []

    for quest_id, quest in quests.items():
        merchant = extract_merchant_from_quest_id(quest_id)
        if merchant:
            entry = build_quest_entry(quest, content_by_id, rewards_by_id)

            # Add chapter info
            ch = quest_to_chapter.get(quest_id)
            if ch:
                entry["chapter_id"] = ch["id"]
                if ch.get("name"):
                    entry["chapter_name"] = ch["name"]
                if ch.get("name_key"):
                    entry["chapter_name_key"] = ch["name_key"]
                if ch.get("order") is not None:
                    entry["chapter_order"] = ch["order"]

            merchant_quests[merchant].append(entry)
        else:
            no_merchant.append(quest_id)

    if no_merchant:
        print(f"  WARNING: {len(no_merchant)} quests could not be mapped to a merchant: {no_merchant[:5]}")

    # Build final merchant list
    merchants_list = []
    for merchant_key in sorted(merchant_quests.keys()):
        quest_list = merchant_quests[merchant_key]
        # Sort quests by chapter order, then by quest number
        quest_list.sort(key=lambda q: (
            q.get("chapter_order", 9999),
            q.get("id", ""),
        ))

        display_name = (
            merchant_names_raw.get(merchant_key)
            or MERCHANT_DISPLAY_NAMES.get(merchant_key)
            or merchant_key
        )

        merchants_list.append({
            "id": merchant_key,
            "name": display_name,
            "portrait": f"/merchant-portraits/Portrait_Merchant_{merchant_key}.png",
            "quest_count": len(quest_list),
            "quests": quest_list,
        })

    # Also build a flat content lookup for reference
    content_summary = {}
    for ctype, directory in CONTENT_DIRS.items():
        content_summary[ctype] = sum(1 for c in content_by_id.values() if c.get("type") == ctype)

    # Stats
    total_quests = sum(m["quest_count"] for m in merchants_list)
    quests_with_objectives = sum(
        1 for m in merchants_list for q in m["quests"] if q.get("objectives")
    )
    quests_with_rewards = sum(
        1 for m in merchants_list for q in m["quests"] if q.get("rewards")
    )

    print(f"\n[build_quests] Summary:")
    print(f"  Total merchants: {len(merchants_list)}")
    print(f"  Total quests: {total_quests}")
    print(f"  Quests with objectives: {quests_with_objectives}")
    print(f"  Quests with rewards: {quests_with_rewards}")
    print(f"  Content entries by type: {content_summary}")

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stats": {
            "total_merchants": len(merchants_list),
            "total_quests": total_quests,
            "quests_with_objectives": quests_with_objectives,
            "quests_with_rewards": quests_with_rewards,
            "content_entries": content_summary,
        },
        "content_lookup": content_by_id,
        "merchants": merchants_list,
    }

    # Write output
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n[build_quests] Written to {OUTPUT_FILE}")
    print(f"  File size: {OUTPUT_FILE.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    build()
