#!/usr/bin/env python3
"""
build_quests.py - Compile all quest data into website/src/data/quests.json

Sources:
  - Localization: Exports/.../Localization/Game/en/Game.json
    (quest titles, greetings, completion texts, chapter names)
  - QuestChapter files: raw/.../Quest/QuestChapter/
    (chapter ordering, quest grouping)
  - Quest files: raw/.../Quest/Quest/
    (required level, prerequisites, inline text/contents for a few quests)
  - QuestReward files: raw/.../Quest/QuestReward/
    (reward items per quest)
  - QuestContent* files: raw/.../Quest/QuestContent*/
    (kill, fetch, escape, explore, hold, damage, props, useitem objectives)

Output: website/src/data/quests.json
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
EXPORTS_ROOT = ROOT.parent / "Exports"
RAW_BASE = ROOT / "raw" / "DungeonCrawler" / "Content" / "DungeonCrawler" / "Data" / "Generated" / "V2"

LOCALIZATION_FILE = (
    EXPORTS_ROOT / "DungeonCrawler" / "Content" / "Localization" / "Game" / "en" / "Game.json"
)

RAW_QUEST = RAW_BASE / "Quest"
QUEST_DIR = RAW_QUEST / "Quest"
CHAPTER_DIR = RAW_QUEST / "QuestChapter"
REWARD_DIR = RAW_QUEST / "QuestReward"

ITEM_METADATA_FILE = ROOT / "website" / "public" / "data" / "item_metadata.json"

# Load item metadata for proper localized names in fetch quests
item_metadata: dict = {}
if ITEM_METADATA_FILE.exists():
    with open(ITEM_METADATA_FILE, encoding="utf-8") as f:
        item_metadata = json.load(f)

CONTENT_DIRS = {
    "Kill":    RAW_QUEST / "QuestContentKill",
    "Fetch":   RAW_QUEST / "QuestContentFetch",
    "Escape":  RAW_QUEST / "QuestContentEscape",
    "Explore": RAW_QUEST / "QuestContentExplore",
    "Hold":    RAW_QUEST / "QuestContentHold",
    "Damage":  RAW_QUEST / "QuestContentDamage",
    "Props":   RAW_QUEST / "QuestContentProps",
    "UseItem": RAW_QUEST / "QuestContentUseItem",
}

OUTPUT_FILE = ROOT / "website" / "public" / "data" / "quests.json"

# ── Portrait overrides (merchant key -> portrait filename token) ───────────────
PORTRAIT_OVERRIDES = {
    "JackOLantern": "PumpkinMan",
    "TavernMaster": "Tavernmaster",
}

# ── Merchant display names ─────────────────────────────────────────────────────
MERCHANT_DISPLAY_NAMES = {
    "Alchemist": "The Alchemist",
    "Armourer": "The Armourer",
    "Cockatrice": "The Cockatrice",
    "Dealmaker": "The Dealmaker",
    "FortuneTeller": "The Fortune Teller",
    "GoblinMerchant": "The Goblin Merchant",
    "Goldsmith": "The Goldsmith",
    "Huntress": "The Huntress",
    "JackOLantern": "Jack O'Lantern",
    "Krampus": "Krampus",
    "Leathersmith": "The Leathersmith",
    "Miner": "The Miner",
    "Navigator": "The Navigator",
    "Nicholas": "Nicholas",
    "NightmareMummy": "The Nightmare Mummy",
    "SkeletonFootman": "The Skeleton Footman",
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

# ── Dungeon tag to friendly name ──────────────────────────────────────────────
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
    "Id.Dungeon.HowlingCrypts": "Howling Crypts",
}


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def load_json_file(path: Path) -> dict | list | None:
    """Load a JSON file with UTF-8 encoding."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"  WARNING: Failed to load {path}: {e}", file=sys.stderr)
        return None


def load_fmodel_json(path: Path) -> dict | None:
    """Load an FModel-exported JSON and return the first object."""
    data = load_json_file(path)
    if isinstance(data, list) and data:
        return data[0]
    return None


def extract_asset_id(ref: dict | None) -> str | None:
    """Extract the asset ID from an AssetPathName reference like '.../Foo.Foo' -> 'Foo'."""
    if not isinstance(ref, dict):
        return None
    path = ref.get("AssetPathName", "")
    if not path:
        return None
    return path.split("/")[-1].split(".")[0] if "/" in path else None


def extract_tag_name(tag: dict | None) -> str | None:
    """Extract TagName from a tag dict."""
    if isinstance(tag, dict):
        return tag.get("TagName")
    return None


def humanize_id(s: str) -> str:
    """Convert PascalCase/camelCase ID to human-readable: DeathSkull -> Death Skull."""
    result = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", s)
    result = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", result)
    result = result.replace("_", " ")
    return result.strip()


def dungeon_tag_to_name(tag: str) -> str:
    """Convert a dungeon tag to a friendly name."""
    return DUNGEON_TAG_NAMES.get(tag, tag.replace("Id.Dungeon.", ""))


def tag_to_name(tag: str, prefix: str) -> str:
    """Strip prefix from a tag and humanize: Id.Monster.Abomination -> Abomination."""
    name = tag[len(prefix):] if tag.startswith(prefix) else tag
    return humanize_id(name)


def module_path_to_name(asset_path: str) -> str:
    """Extract a readable module name from an asset path."""
    asset_id = asset_path.split(".")[-1] if "." in asset_path else asset_path
    name = asset_id
    if name.startswith("Id_DungeonModule_"):
        name = name[17:]
    return name.replace("_", " ").strip()


# ═══════════════════════════════════════════════════════════════════════════════
# Localization
# ═══════════════════════════════════════════════════════════════════════════════

def load_localization() -> dict[str, str]:
    """Load the DC namespace from the localization file."""
    print(f"[loc] Loading {LOCALIZATION_FILE}")
    data = load_json_file(LOCALIZATION_FILE)
    if not data or not isinstance(data, dict):
        print("  ERROR: Could not load localization!", file=sys.stderr)
        return {}
    dc = data.get("DC", {})
    print(f"  {len(dc)} entries in DC namespace")
    return dc


def _version_sort_key(suffix: str) -> tuple[int, int]:
    """Sort version suffixes: EAS > EA, then by number."""
    m = re.match(r"_?(EAS?)_(\d+)$", suffix)
    if m:
        era = 1 if m.group(1) == "EAS" else 0
        return (era, int(m.group(2)))
    return (-1, 0)


def resolve_localized(loc: dict[str, str], prefix: str) -> str | None:
    """
    Given a key prefix like 'Text_DesignData_Quest_Alchemist_Title_01',
    find the latest-versioned entry (e.g. _EAS_08 beats _EA_05).
    Also tries exact match (some keys have no version suffix).
    """
    if prefix in loc:
        # Could be an exact match with no version suffix
        candidates = {prefix: ("", loc[prefix])}
    else:
        candidates = {}

    for k, v in loc.items():
        if k.startswith(prefix) and k != prefix:
            suffix = k[len(prefix):]
            # Must look like a version suffix (_EA_05, _EAS_06, etc.)
            if re.match(r"^_E", suffix):
                candidates[k] = (suffix, v)

    if not candidates:
        return None
    if len(candidates) == 1:
        return list(candidates.values())[0][1] if isinstance(list(candidates.values())[0], tuple) else list(candidates.values())[0]

    # Pick latest version
    best_key = max(candidates, key=lambda k: _version_sort_key(
        candidates[k][0] if isinstance(candidates[k], tuple) else ""
    ))
    val = candidates[best_key]
    return val[1] if isinstance(val, tuple) else val


def build_loc_indices(loc: dict[str, str]):
    """
    Build lookup dicts for quest titles, greetings, completions.
    Key: (merchant_loc_key, quest_number_str) -> text
    """
    title_idx: dict[tuple[str, str], str] = {}
    greeting_idx: dict[tuple[str, str], str] = {}
    complete_idx: dict[tuple[str, str], str] = {}

    # Patterns:
    #   Text_DesignData_Quest_{MerchantKey}_Title_{NN}_{version}
    #   Text_DesignData_Quest_{MerchantKey}_Greeting_{NN}_{version}
    #   Text_DesignData_Quest_{MerchantKey}_Complete_{NN}_{version}
    # MerchantKey can contain underscores (e.g. TavernMaster_Final, Huntress_Daily)
    #
    # Some quests have qualifiers before the number:
    #   Quest_GoblinMerchant_Title_Final_01 -> merchant=GoblinMerchant, num_part=Final_01
    #   Quest_TavernMaster_Tuto_Title_01    -> merchant=TavernMaster_Tuto, num_part=01
    # The qualifier (Final/Tuto) can be part of the merchant key OR between Title and number.
    #
    # We use a pattern that captures optional qualifier + number after Title/Greeting/Complete.
    title_re = re.compile(r"^Text_DesignData_Quest_(.+?)_Title_((?:[A-Za-z]+_)?\d+)")
    greeting_re = re.compile(r"^Text_DesignData_Quest_(.+?)_Greeting_((?:[A-Za-z]+_)?\d+)")
    complete_re = re.compile(r"^Text_DesignData_Quest_(.+?)_Complete_((?:[A-Za-z]+_)?\d+)")

    def _collect(pattern: re.Pattern, idx: dict):
        # First pass: find all unique (merchant, number_part) prefixes
        prefixes: set[tuple[str, str, str]] = set()
        for k in loc:
            m = pattern.match(k)
            if m:
                merchant = m.group(1)
                num_part = m.group(2)  # e.g. "01" or "Final_01"
                prefix = k[: m.end()]
                prefixes.add((merchant, num_part, prefix))

        # Second pass: resolve each to best version
        for merchant, num_part, prefix in prefixes:
            text = resolve_localized(loc, prefix)
            # Skip entries where the value is the key itself (unlocalized placeholder)
            if text and not text.startswith("Text_DesignData_"):
                idx[(merchant, num_part)] = text

    _collect(title_re, title_idx)
    _collect(greeting_re, greeting_idx)
    _collect(complete_re, complete_idx)

    print(f"  Loc indices: {len(title_idx)} titles, {len(greeting_idx)} greetings, {len(complete_idx)} completions")
    return title_idx, greeting_idx, complete_idx


# ═══════════════════════════════════════════════════════════════════════════════
# Quest Chapters
# ═══════════════════════════════════════════════════════════════════════════════

def _derive_merchant_key(chapter_id: str, quest_ids: list[str]) -> str:
    """
    Derive the merchant key from a chapter/quest.
    Uses the first quest ID if available, otherwise the chapter ID.
    """
    if quest_ids:
        rest = quest_ids[0].replace("Id_Quest_", "")
        return re.sub(r"_\d+$", "", rest)

    rest = chapter_id.replace("Id_QuestChapter_", "")
    return re.sub(r"_\d+$", "", rest)


def load_chapters() -> tuple[dict[str, list[dict]], dict[str, dict]]:
    """
    Load all QuestChapter files.
    Returns:
      merchant_chapters: merchant_key -> [chapter_data, ...] sorted by order
      chapter_map: chapter_id -> chapter_data
    """
    print(f"[chapters] Loading from {CHAPTER_DIR}")
    merchant_chapters: dict[str, list[dict]] = defaultdict(list)
    chapter_map: dict[str, dict] = {}

    for f in sorted(CHAPTER_DIR.glob("*.json")):
        obj = load_fmodel_json(f)
        if not obj:
            continue

        props = obj.get("Properties", {})
        chapter_id = obj.get("Name", f.stem)

        name_data = props.get("Name", {})
        chapter_name = name_data.get("LocalizedString", "") if isinstance(name_data, dict) else ""
        order = props.get("Order", 0)

        quest_ids = []
        for q in props.get("Quests", []):
            qid = extract_asset_id(q)
            if qid:
                quest_ids.append(qid)

        merchant_key = _derive_merchant_key(chapter_id, quest_ids)

        # Extract original chapter number from the localization key
        name_key = name_data.get("Key", "") if isinstance(name_data, dict) else ""
        loc_key_match = re.search(r"_(\d+)_[A-Z]", name_key)
        loc_key_num = int(loc_key_match.group(1)) if loc_key_match else 0

        ch = {
            "chapter_id": chapter_id,
            "name": chapter_name,
            "order": order,
            "quest_ids": quest_ids,
            "merchant_key": merchant_key,
            "loc_key_num": loc_key_num,
        }
        merchant_chapters[merchant_key].append(ch)
        chapter_map[chapter_id] = ch

    # Sort each merchant's chapters by order
    for mk in merchant_chapters:
        merchant_chapters[mk].sort(key=lambda c: c["order"])

    total = sum(len(v) for v in merchant_chapters.values())
    print(f"  {total} chapters across {len(merchant_chapters)} merchant keys")
    return dict(merchant_chapters), chapter_map


def build_title_remap(merchant_chapters: dict[str, list[dict]]) -> dict[str, int]:
    """
    Build a quest_id -> remapped_title_number dict.

    Some merchants had their chapters reordered after titles were assigned.
    The localization title numbers follow the ORIGINAL chapter order (loc_key_num),
    not the current display order. For reordered merchants, we need to map each
    quest to the correct title number based on its chapter's loc_key_num.

    Formula: title_start = ((loc_key + 1) % num_orig_chapters) * qpc + 1
    Only applies to the first batch of reordered chapters (loc_keys form a
    permutation). Later-added chapters use 1:1 mapping.
    """
    remap: dict[str, int] = {}

    for merchant_key, chapters in merchant_chapters.items():
        # Skip sub-type merchants
        if any(s in merchant_key for s in _SUB_SUFFIXES):
            continue

        # Chapters sorted by display order
        chapters_sorted = sorted(chapters, key=lambda c: c["order"])
        if not chapters_sorted:
            continue

        qpc = len(chapters_sorted[0]["quest_ids"])
        if qpc == 0:
            continue

        # Check if first N chapters are reordered
        # (their loc_key_nums form a permutation but not in sequential order)
        loc_keys = [c["loc_key_num"] for c in chapters_sorted]

        # Find the SMALLEST N where first N loc_keys form a permutation AND are reordered.
        # The original reordered batch is the first N chapters whose loc_keys are
        # a shuffle of 1..N. Later chapters (with sequential loc_keys) were added after.
        num_orig = 0
        for n in range(2, min(len(loc_keys) + 1, 7)):
            first_n = sorted(loc_keys[:n])
            is_perm = (len(set(first_n)) == n and first_n == list(range(1, n + 1)))
            is_reordered = (loc_keys[:n] != first_n)
            if is_perm and is_reordered:
                num_orig = n
                break

        if num_orig > 0:
            # Reordered merchant: apply formula to first num_orig chapters
            for ch_idx, ch in enumerate(chapters_sorted):
                for pos, qid in enumerate(ch["quest_ids"]):
                    if ch_idx < num_orig:
                        title_num = ((ch["loc_key_num"] + 1) % num_orig) * qpc + pos + 1
                        if title_num <= 0:
                            title_num += num_orig * qpc
                    else:
                        # Later chapter: use quest number directly
                        q_match = re.search(r"_(\d+)$", qid)
                        title_num = int(q_match.group(1)) if q_match else 0
                    remap[qid] = title_num

            print(f"  Remap: {merchant_key} - {num_orig} reordered chapters (qpc={qpc})")
        # Non-reordered: no entry in remap (will use default 1:1)

    return remap


# ═══════════════════════════════════════════════════════════════════════════════
# Quest Files
# ═══════════════════════════════════════════════════════════════════════════════

def load_quests() -> dict[str, dict]:
    """Load all Quest files. Returns quest_id -> parsed data."""
    print(f"[quests] Loading from {QUEST_DIR}")
    quests: dict[str, dict] = {}

    for f in sorted(QUEST_DIR.glob("*.json")):
        obj = load_fmodel_json(f)
        if not obj:
            continue

        quest_id = obj.get("Name", f.stem)
        props = obj.get("Properties", {})

        q: dict = {}
        q["required_level"] = props.get("RequiredLevel", 0)

        # Prerequisite
        prereq = extract_asset_id(props.get("RequiredQuest"))
        if prereq:
            q["prerequisite_id"] = prereq

        # Explicit reward reference (some quests like Valentine have it inline)
        reward_ref = extract_asset_id(props.get("QuestReward"))
        if reward_ref:
            q["reward_ref"] = reward_ref

        # Inline localized text (only a handful of quests have these resolved)
        for field, key in [("TitleText", "title"), ("GreetingText", "greeting"),
                           ("CompleteText", "completion")]:
            text_obj = props.get(field)
            if isinstance(text_obj, dict):
                localized = text_obj.get("LocalizedString", "")
                loc_key = text_obj.get("Key", "")
                # If LocalizedString != Key, it's resolved inline
                if localized and localized != loc_key and not localized.startswith("Text_DesignData"):
                    q[f"inline_{key}"] = localized

        # Explicit QuestContents (only ~6 quests have this)
        content_ids = []
        for c in props.get("QuestContents", []):
            cid = extract_asset_id(c)
            if cid:
                content_ids.append(cid)
        if content_ids:
            q["content_ids"] = content_ids

        quests[quest_id] = q

    print(f"  {len(quests)} quests loaded")
    return quests


# ═══════════════════════════════════════════════════════════════════════════════
# Quest Rewards
# ═══════════════════════════════════════════════════════════════════════════════

def _parse_random_reward_id(reward_id: str) -> tuple[str | None, str | None]:
    """Parse rarity and item type from a random reward ID."""
    parts = reward_id.replace("Id_RandomReward_Quest_", "").split("_")
    rarities = {"Common", "Uncommon", "Rare", "Epic", "Legendary", "Unique"}
    type_words = {"Weapon", "Weapons", "Armor", "Armors", "Accessory", "Accessories", "Utility"}
    rarity = item_type = None
    for p in parts:
        if p in rarities:
            rarity = p
        elif p in type_words:
            item_type = p.rstrip("s")
            if item_type == "Accessorie":
                item_type = "Accessory"
    return rarity, item_type


def load_rewards() -> dict[str, list[dict]]:
    """Load all QuestReward files. Returns reward_id -> [reward entries]."""
    print(f"[rewards] Loading from {REWARD_DIR}")
    rewards: dict[str, list[dict]] = {}

    for f in sorted(REWARD_DIR.glob("*.json")):
        obj = load_fmodel_json(f)
        if not obj:
            continue

        reward_id = obj.get("Name", f.stem)
        props = obj.get("Properties", {})
        items = []

        for ri in props.get("RewardItemArray", []):
            rtype_raw = ri.get("RewardType", "")
            rtype = rtype_raw.split("::")[-1] if "::" in rtype_raw else rtype_raw
            rid = ri.get("RewardId", "")
            count = ri.get("RewardCount", 0)

            entry: dict = {"type": rtype, "count": count}

            if rtype == "Item":
                entry["id"] = rid
                clean = rid.replace("Id_Item_", "") if rid.startswith("Id_Item_") else rid
                entry["name"] = humanize_id(clean)

            elif rtype == "Exp":
                pass  # type + count only

            elif rtype == "Affinity":
                merchant = rid.replace("Id_Merchant_", "") if rid.startswith("Id_Merchant_") else rid
                entry["merchant"] = merchant

            elif rtype == "Random":
                entry["id"] = rid
                rarity, itype = _parse_random_reward_id(rid)
                if rarity:
                    entry["rarity"] = rarity
                if itype:
                    entry["item_type"] = itype

            else:
                entry["id"] = rid

            # Preserve explicit ItemRarity / ItemType if present
            ir = ri.get("ItemRarity", "")
            if ir:
                ir_clean = ir.split("::")[-1] if "::" in ir else ir
                if ir_clean and "rarity" not in entry:
                    entry["rarity"] = ir_clean
            it = ri.get("ItemType", "")
            if it:
                it_clean = it.split("::")[-1] if "::" in it else it
                if it_clean and "item_type" not in entry:
                    entry["item_type"] = it_clean

            items.append(entry)

        rewards[reward_id] = items

    print(f"  {len(rewards)} reward sets loaded")
    return rewards


# ═══════════════════════════════════════════════════════════════════════════════
# Quest Content (Objectives)
# ═══════════════════════════════════════════════════════════════════════════════

def load_all_content() -> dict[str, dict]:
    """Load all quest content files from all content type directories."""
    print("[content] Loading quest objectives...")
    lookup: dict[str, dict] = {}

    for ctype, dirpath in CONTENT_DIRS.items():
        if not dirpath.is_dir():
            print(f"  WARNING: {ctype} dir not found: {dirpath}", file=sys.stderr)
            continue

        count = 0
        for f in sorted(dirpath.glob("*.json")):
            obj = load_fmodel_json(f)
            if not obj:
                continue

            cid = obj.get("Name", f.stem)
            props = obj.get("Properties", {})
            entry: dict = {"id": cid, "content_type": ctype}

            # Common
            entry["count"] = props.get("ContentCount", 0)
            if props.get("SingleSession"):
                entry["single_session"] = True

            # Dungeons
            dungeons = []
            for dtag in props.get("DungeonIdTags", []):
                tag = extract_tag_name(dtag)
                if tag:
                    dungeons.append(dungeon_tag_to_name(tag))
            if dungeons:
                entry["dungeons"] = dungeons

            # Type-specific
            if ctype == "Kill":
                kt = props.get("KillType", "")
                entry["kill_type"] = kt.split("::")[-1] if "::" in kt else kt
                kill_tag = extract_tag_name(props.get("KillTag"))
                if kill_tag:
                    entry["target"] = tag_to_name(kill_tag, "Id.Monster.")
                    entry["target_tag"] = kill_tag
                desc = f"Kill {entry['count']} {entry.get('target', '?')}"
                if dungeons:
                    desc += f" in {', '.join(dungeons)}"
                entry["description"] = desc

            elif ctype == "Fetch":
                item_tag = extract_tag_name(props.get("ItemIdTag"))
                if item_tag:
                    item_key = item_tag.replace("Id.Item.", "")
                    entry["item"] = item_key
                    # Use localized name from item_metadata if available
                    if item_key in item_metadata:
                        entry["item_name"] = item_metadata[item_key]["name"]
                    else:
                        entry["item_name"] = tag_to_name(item_tag, "Id.Item.")
                ls = props.get("ItemLootState", "")
                if ls:
                    entry["loot_state"] = ls.split("::")[-1] if "::" in ls else ls
                # RarityType is a tag dict: {"TagName": "Type.Item.Rarity.Epic"}
                rarity_tag = extract_tag_name(props.get("RarityType"))
                if rarity_tag:
                    entry["rarity"] = rarity_tag.split(".")[-1]  # "Type.Item.Rarity.Epic" -> "Epic"
                else:
                    # Fallback to legacy ItemRarity field
                    ir = props.get("ItemRarity", "")
                    if ir:
                        entry["rarity"] = ir.split("::")[-1] if "::" in ir else ir
                type_tag = extract_tag_name(props.get("TypeTag"))
                if type_tag:
                    entry["item_type_tag"] = tag_to_name(type_tag, "Type.Item.")
                desc = f"Collect {entry['count']} {entry.get('item_name', entry.get('item_type_tag', '?'))}"
                if entry.get("rarity"):
                    desc = f"Collect {entry['count']} {entry['rarity']} {entry.get('item_name', '?')}"
                entry["description"] = desc

            elif ctype == "Escape":
                desc = f"Escape {entry['count']} time(s)"
                if dungeons:
                    desc += f" from {', '.join(dungeons)}"
                if props.get("ConsecutiveEscape"):
                    entry["consecutive"] = True
                    desc += " (consecutive)"
                entry["description"] = desc

            elif ctype == "Explore":
                mod = props.get("ModuleId")
                if isinstance(mod, dict) and mod.get("AssetPathName"):
                    entry["module"] = module_path_to_name(mod["AssetPathName"])
                desc = f"Explore {entry.get('module', '?')}"
                if dungeons:
                    desc += f" in {', '.join(dungeons)}"
                entry["description"] = desc

            elif ctype == "Hold":
                mod = props.get("ModuleId")
                if isinstance(mod, dict) and mod.get("AssetPathName"):
                    entry["module"] = module_path_to_name(mod["AssetPathName"])
                entry["hold_time"] = props.get("HoldTime", 0)
                if props.get("MustEscape"):
                    entry["must_escape"] = True
                desc = f"Hold {entry.get('module', '?')} for {entry.get('hold_time', '?')}s"
                entry["description"] = desc

            elif ctype == "Damage":
                dt = props.get("DamageType", "")
                entry["damage_type"] = dt.split("::")[-1] if "::" in dt else dt
                desc = f"Deal {entry['count']} damage ({entry['damage_type']})"
                entry["description"] = desc

            elif ctype == "Props":
                pt = props.get("PropsType", "")
                entry["props_type"] = pt.split("::")[-1] if "::" in pt else pt
                ptag = extract_tag_name(props.get("PropsIdTag"))
                if ptag:
                    entry["target"] = tag_to_name(ptag, "Id.Props.")
                desc = f"{entry.get('props_type', 'Interact')} {entry['count']} {entry.get('target', '?')}"
                if dungeons:
                    desc += f" in {', '.join(dungeons)}"
                entry["description"] = desc

            elif ctype == "UseItem":
                item_tag = extract_tag_name(props.get("ItemIdTag"))
                if item_tag:
                    entry["item"] = item_tag.replace("Id.Item.", "")
                    entry["item_name"] = tag_to_name(item_tag, "Id.Item.")
                it = props.get("ItemType", "")
                if it:
                    entry["item_type"] = it.split("::")[-1] if "::" in it else it
                desc = f"Use {entry['count']} {entry.get('item_name', '?')}"
                if dungeons:
                    desc += f" in {', '.join(dungeons)}"
                entry["description"] = desc

            lookup[cid] = entry
            count += 1

        print(f"  {ctype}: {count} entries")

    print(f"  Total: {len(lookup)} content entries")
    return lookup


# ═══════════════════════════════════════════════════════════════════════════════
# Key derivation helpers
# ═══════════════════════════════════════════════════════════════════════════════

def get_quest_number(quest_id: str) -> str | None:
    """Id_Quest_Alchemist_01 -> '01'."""
    m = re.search(r"_(\d+)$", quest_id)
    return m.group(1) if m else None


def get_merchant_quest_key(quest_id: str) -> str:
    """
    Id_Quest_Alchemist_01 -> 'Alchemist'
    Id_Quest_TavernMaster_Final_01 -> 'TavernMaster_Final'
    """
    rest = quest_id.replace("Id_Quest_", "")
    return re.sub(r"_\d+$", "", rest)


def get_loc_lookup_keys(quest_id: str) -> list[tuple[str, str]]:
    """
    Return a list of (merchant_loc_key, num_part) candidates to try
    when looking up localization for a quest. First match wins.

    Examples:
      Id_Quest_Alchemist_01          -> [("Alchemist", "01")]
      Id_Quest_GoblinMerchant_Final_01 -> [("GoblinMerchant_Final", "01"),
                                           ("GoblinMerchant", "Final_01")]
      Id_Quest_TavernMaster_Tuto_01  -> [("TavernMaster_Tuto", "01"),
                                           ("TavernMaster", "Tuto_01")]
      Id_Quest_Huntress_Daily_Equipment_01 -> [("Huntress_Daily_Equipment", "01"),
                                                ("Huntress_Daily", "01")]
      Id_Quest_Huntress_Daily_05     -> [("Huntress_Daily", "05"),
                                          ("Huntress_Daily", "01")]
    """
    merchant_key = get_merchant_quest_key(quest_id)
    qnum = get_quest_number(quest_id)
    if not qnum:
        return [(merchant_key, "01")]

    candidates = [(merchant_key, qnum)]

    # For sub-type merchants (Final, Tuto, Extra), also try the base merchant
    # with the qualifier prepended to the number
    for suffix in ["_Final", "_Tuto", "_Extra"]:
        if merchant_key.endswith(suffix):
            base = merchant_key[: -len(suffix)]
            qualifier = suffix.lstrip("_")
            candidates.append((base, f"{qualifier}_{qnum}"))
            break

    # Huntress_Daily_Equipment shares text with Huntress_Daily
    if merchant_key == "Huntress_Daily_Equipment":
        candidates.append(("Huntress_Daily", qnum))

    # For daily/weekly/seasonal quests with many numbered variants but only
    # one localization entry (key 01), fall back to 01
    if qnum != "01":
        for sub in ["_Daily", "_Weekly", "_Seasonal", "_Sesonal"]:
            if merchant_key.endswith(sub):
                candidates.append((merchant_key, "01"))
                break

    return candidates


_SUB_SUFFIXES = [
    "_Daily_Equipment", "_Daily", "_Weekly", "_Seasonal", "_Sesonal",
    "_Final", "_Tuto", "_Extra",
]


def get_base_merchant(merchant_key: str) -> str:
    """
    TavernMaster_Final -> TavernMaster
    Huntress_Daily -> Huntress
    Krampus_Seasonal -> Krampus
    """
    for s in sorted(_SUB_SUFFIXES, key=len, reverse=True):
        if merchant_key.endswith(s):
            return merchant_key[: -len(s)]
    return merchant_key


def get_portrait_path(base_merchant: str) -> str:
    token = PORTRAIT_OVERRIDES.get(base_merchant, base_merchant)
    return f"/merchant-portraits/Portrait_Merchant_{token}.png"


# ═══════════════════════════════════════════════════════════════════════════════
# Main build
# ═══════════════════════════════════════════════════════════════════════════════

def build():
    loc = load_localization()
    title_idx, greeting_idx, complete_idx = build_loc_indices(loc)
    merchant_chapters, chapter_map = load_chapters()
    title_remap = build_title_remap(merchant_chapters)
    quests = load_quests()
    rewards = load_rewards()
    content_lookup = load_all_content()

    print(f"  Item metadata: {len(item_metadata)} items loaded")

    # Load uasset-derived quest-to-objective mapping
    uasset_map_path = ROOT / "extracted" / "quest_objective_map.json"
    uasset_obj_map: dict[str, list[str]] = {}
    if uasset_map_path.exists():
        with open(uasset_map_path, encoding="utf-8") as f:
            uasset_obj_map = json.load(f)
        print(f"  Loaded uasset objective map: {len(uasset_obj_map)} quests")
    else:
        print("  WARNING: quest_objective_map.json not found - objectives will be limited")

    # Build reward lookup: quest_id -> reward_id (by naming convention)
    quest_reward_map: dict[str, str] = {}
    for rid in rewards:
        qid = rid.replace("Id_Reward_Quest_", "Id_Quest_")
        quest_reward_map[qid] = rid

    # Group chapters by base merchant (all sub-types under one merchant)
    base_merchant_chapters: dict[str, list[dict]] = defaultdict(list)
    for mk, chaps in merchant_chapters.items():
        base = get_base_merchant(mk)
        base_merchant_chapters[base].extend(chaps)

    # Sort chapters within each base merchant by order
    for base in base_merchant_chapters:
        base_merchant_chapters[base].sort(key=lambda c: c["order"])

    # Track coverage
    quests_in_chapters: set[str] = set()
    for chaps in merchant_chapters.values():
        for ch in chaps:
            for qid in ch["quest_ids"]:
                quests_in_chapters.add(qid)

    orphans = set(quests.keys()) - quests_in_chapters
    if orphans:
        print(f"\n  Note: {len(orphans)} quests not in any chapter (will be appended): {sorted(orphans)[:8]}...")

    # ── Build output per merchant ──────────────────────────────────────────
    merchants_output = []

    for base_merchant in sorted(base_merchant_chapters.keys()):
        chaps = base_merchant_chapters[base_merchant]
        display_name = MERCHANT_DISPLAY_NAMES.get(base_merchant, base_merchant)
        portrait = get_portrait_path(base_merchant)

        chapters_out = []
        for ch in chaps:
            quests_out = []
            for idx, quest_id in enumerate(ch["quest_ids"]):
                qdata = quests.get(quest_id, {})
                qnum = get_quest_number(quest_id)
                loc_keys = get_loc_lookup_keys(quest_id)

                # Apply title remap for merchants with reordered chapters
                if quest_id in title_remap:
                    remapped_num = f"{title_remap[quest_id]:02d}"
                    merchant_key = get_merchant_quest_key(quest_id)
                    loc_keys = [(merchant_key, remapped_num)] + loc_keys

                def _loc_lookup(idx_dict, inline_key):
                    """Try inline text first, then loc index with multiple candidate keys."""
                    val = qdata.get(inline_key)
                    if val:
                        return val
                    for mk, np in loc_keys:
                        val = idx_dict.get((mk, np))
                        if val:
                            return val
                    return None

                # ── Title ──
                title = _loc_lookup(title_idx, "inline_title")
                if not title:
                    # Generate readable name: Id_Quest_Alchemist_16 -> "Alchemist Quest 16"
                    m_title = re.match(r"Id_Quest_(\w+?)_(\d+)$", quest_id)
                    if m_title:
                        merchant_part = re.sub(r"([a-z])([A-Z])", r"\1 \2", m_title.group(1))
                        title = f"{merchant_part} Quest {int(m_title.group(2))}"
                    else:
                        title = quest_id

                # ── Greeting ──
                greeting = _loc_lookup(greeting_idx, "inline_greeting")

                # ── Completion ──
                completion = _loc_lookup(complete_idx, "inline_completion")

                # ── Prerequisite ──
                prerequisite = None
                prereq_id = qdata.get("prerequisite_id")
                if prereq_id:
                    prereq_keys = get_loc_lookup_keys(prereq_id)
                    # Apply remap for prerequisites too
                    if prereq_id in title_remap:
                        rn = f"{title_remap[prereq_id]:02d}"
                        pmk = get_merchant_quest_key(prereq_id)
                        prereq_keys = [(pmk, rn)] + prereq_keys
                    prereq_title = None
                    for mk, np in prereq_keys:
                        prereq_title = title_idx.get((mk, np))
                        if prereq_title:
                            break
                    prerequisite = {
                        "id": prereq_id,
                        "title": prereq_title or prereq_id,
                    }

                # ── Rewards ──
                reward_items: list[dict] = []
                rref = qdata.get("reward_ref")
                if rref and rref in rewards:
                    reward_items = rewards[rref]
                elif quest_id in quest_reward_map:
                    reward_items = rewards[quest_reward_map[quest_id]]

                # ── Objectives ──
                objectives: list[dict] = []
                # First try uasset-derived mapping (covers all 553 quests)
                uasset_content_ids = uasset_obj_map.get(quest_id, [])
                for cid in uasset_content_ids:
                    if cid in content_lookup:
                        objectives.append(content_lookup[cid])
                # Fall back to inline content_ids from JSON (only 6 quests)
                if not objectives:
                    for cid in qdata.get("content_ids", []):
                        if cid in content_lookup:
                            objectives.append(content_lookup[cid])

                # ── Dungeons from objectives ──
                dungeon_set: set[str] = set()
                for obj in objectives:
                    for d in obj.get("dungeons", []):
                        dungeon_set.add(d)

                quest_entry: dict = {
                    "id": quest_id,
                    "title": title,
                    "quest_number": int(qnum) if qnum else idx + 1,
                    "required_level": qdata.get("required_level", 0),
                }
                if greeting:
                    quest_entry["greeting"] = greeting
                if completion:
                    quest_entry["completion_text"] = completion
                if prerequisite:
                    quest_entry["prerequisite"] = prerequisite
                quest_entry["dungeons"] = sorted(dungeon_set) if dungeon_set else []
                quest_entry["objectives"] = objectives
                quest_entry["rewards"] = reward_items

                quests_out.append(quest_entry)

            chapters_out.append({
                "name": ch["name"],
                "order": ch["order"],
                "quests": quests_out,
            })

        merchants_output.append({
            "id": base_merchant,
            "name": display_name,
            "portrait": portrait,
            "chapters": chapters_out,
        })

    # ── Stats ──────────────────────────────────────────────────────────────
    total_quests = sum(len(q["quests"]) for m in merchants_output for q in m["chapters"])
    with_title = sum(
        1 for m in merchants_output for ch in m["chapters"] for q in ch["quests"]
        if q["title"] and not q["title"].startswith("Id_Quest_")
    )
    with_greeting = sum(
        1 for m in merchants_output for ch in m["chapters"] for q in ch["quests"]
        if q.get("greeting")
    )
    with_rewards = sum(
        1 for m in merchants_output for ch in m["chapters"] for q in ch["quests"]
        if q.get("rewards")
    )
    with_objectives = sum(
        1 for m in merchants_output for ch in m["chapters"] for q in ch["quests"]
        if q.get("objectives")
    )

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "Game data files (FModel extraction + localization)",
        "total_quests": total_quests,
        "total_merchants": len(merchants_output),
        "merchants": merchants_output,
        "content_lookup": content_lookup,
    }

    # ── Write ──────────────────────────────────────────────────────────────
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    size_kb = OUTPUT_FILE.stat().st_size / 1024
    print(f"\n{'='*60}")
    print(f"Output: {OUTPUT_FILE}")
    print(f"Size:   {size_kb:.1f} KB")
    print(f"{'='*60}")
    print(f"  Merchants:            {len(merchants_output)}")
    print(f"  Total quests:         {total_quests}")
    print(f"  With resolved title:  {with_title}/{total_quests}")
    print(f"  With greeting text:   {with_greeting}/{total_quests}")
    print(f"  With rewards:         {with_rewards}/{total_quests}")
    print(f"  With objectives:      {with_objectives}/{total_quests}")
    print(f"  Content lookup:       {len(content_lookup)} entries")

    # -- Sample --
    if merchants_output:
        m = merchants_output[0]
        print(f"\n-- Sample: {m['name']} --")
        if m["chapters"]:
            ch = m["chapters"][0]
            print(f"  Chapter: \"{ch['name']}\" (order {ch['order']})")
            for q in ch["quests"][:2]:
                print(f"    [{q['quest_number']}] {q['title']}  (level {q['required_level']})")
                if q.get("greeting"):
                    g = q["greeting"][:90].encode("ascii", "replace").decode()
                    print(f"        Greeting: {g}...")
                if q.get("rewards"):
                    print(f"        Rewards: {len(q['rewards'])} items")


if __name__ == "__main__":
    build()
