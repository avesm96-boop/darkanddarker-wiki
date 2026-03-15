"""
Build website/public/data/items.json — item finder data for the wiki.

Architecture matches the reference project (build_item_finder.pl):
  Items are grouped by BASE NAME (rarity suffix stripped).
  Loot chain: Spawner → LootDropGroup (grade fallback) → LootDrop (pool) + LootDropRate
  Probability computed client-side using pools, rates, and luck curve.

Key concepts:
  - LuckGrade (LG) 0-8: LG0=Nothing, LG1=Poor, LG2=Common, ... LG8=Artifact
  - Each LootDrop pool has items at various LGs
  - Each LootDropRate has rates per LG (0-8)
  - Drop chance: rate[lg] / sum(rates) * (1 / items_at_that_lg_in_pool)
  - Multi-roll: 1 - (1-p)^count
  - CT_LuckGrade curve modifies rates per LG based on player luck stat

Usage:
    py tools/build_item_search.py
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED = ROOT / "extracted"
RAW_MAPS_DIR = ROOT / "raw" / "DungeonCrawler" / "Content" / "DungeonCrawler" / "Maps" / "Dungeon" / "Modules"
PROPS_V2_DIR = ROOT.parent / "Exports" / "DungeonCrawler" / "Content" / "DungeonCrawler" / "Data" / "Generated" / "V2" / "Props" / "Props"
ICON_DIR = ROOT / "website" / "public" / "item-icons"
OUT_FILE = ROOT / "website" / "public" / "data" / "items.json"

# ---------------------------------------------------------------------------
# Dungeon configuration — 8 sub-zones, each with 3 difficulties
# ---------------------------------------------------------------------------

DUNGEONS = [
    {"name": "Ship Graveyard", "grades": [(1031, "Adventure"), (2031, "Normal"), (3031, "High Roller")]},
    {"name": "Goblin Cave",    "grades": [(1001, "Adventure"), (2001, "Normal"), (3001, "High Roller")]},
    {"name": "Firedeep",       "grades": [(1002, "Adventure"), (2002, "Normal"), (3002, "High Roller")]},
    {"name": "Ice Cavern",     "grades": [(1011, "Adventure"), (2011, "Normal"), (3011, "High Roller")]},
    {"name": "Ice Abyss",      "grades": [(1012, "Adventure"), (2012, "Normal"), (3012, "High Roller")]},
    {"name": "Ruins",          "grades": [(1021, "Adventure"), (2021, "Normal"), (3021, "High Roller")]},
    {"name": "Crypt",          "grades": [(1022, "Adventure"), (2022, "Normal"), (3022, "High Roller")]},
    {"name": "Inferno",        "grades": [(1023, "Adventure"), (2023, "Normal"), (3023, "High Roller")]},
]

# Map directory name → dungeon name (for spawner placement)
MAP_DIR_TO_DUNGEON: dict[str, str] = {
    "Cave":          "Goblin Cave",
    "Firedeep":      "Firedeep",
    "IceCave":       "Ice Cavern",
    "IceAbyss":      "Ice Abyss",
    "Crypt":         "Crypt",
    "Ruins":         "Ruins",
    "Inferno":       "Inferno",
    "ShipGraveyard": "Ship Graveyard",
}

# Rarity names indexed by luck grade
RARITIES = ["Nothing", "Poor", "Common", "Uncommon", "Rare", "Epic", "Legendary", "Unique", "Artifact"]

RARITY_FROM_TAG = {
    "Type.Item.Rarity.Poor":      1,
    "Type.Item.Rarity.Common":    2,
    "Type.Item.Rarity.Uncommon":  3,
    "Type.Item.Rarity.Rare":      4,
    "Type.Item.Rarity.Epic":      5,
    "Type.Item.Rarity.Legend":    6,
    "Type.Item.Rarity.Unique":    7,
    "Type.Item.Rarity.Artifact":  8,
}

# CT_LuckGrade — sampled at luck 0, 0.5, 1, 1.5, ..., 5.0 (11 values per LG)
# Source: raw/DungeonCrawler/Content/DungeonCrawler/Data/GameplayAbility/CT_LuckGrade.json
LUCK_CURVE = [
    [1, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55, 0.5],       # LG0
    [1, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55, 0.5],       # LG1
    [1, 0.975, 0.95, 0.925, 0.9, 0.875, 0.85, 0.825, 0.8, 0.775, 0.75],# LG2
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],                                  # LG3
    [1, 1.143, 1.27, 1.383, 1.481, 1.563, 1.631, 1.684, 1.721, 1.744, 1.752],  # LG4
    [1, 1.301, 1.57, 1.807, 2.013, 2.188, 2.33, 2.441, 2.521, 2.568, 2.584],  # LG5
    [1, 1.433, 1.82, 2.162, 2.458, 2.709, 2.914, 3.073, 3.188, 3.256, 3.28],  # LG6
    [1, 1.514, 1.973, 2.379, 2.73, 3.028, 3.271, 3.461, 3.596, 3.678, 3.705], # LG7
    [1, 1.61, 2.156, 2.637, 3.055, 3.408, 3.697, 3.922, 4.083, 4.18, 4.213],  # LG8
]

# ---------------------------------------------------------------------------
# Category classification (from reference project)
# ---------------------------------------------------------------------------

CATEGORY_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("Monster",        re.compile(r"Monster_")),
    ("NPC",            re.compile(r"NPC_")),
    ("TreasureHoard",  re.compile(r"Props_Hoard|Props_SuperHoard")),
    ("MarvelousChest", re.compile(r"Props_MarvelousChest")),
    ("GoldChest",      re.compile(r"Props_GoldChest")),
    ("OrnateChest",    re.compile(r"Props_OrnateChest")),
    ("SpecialChest",   re.compile(r"Props_ChestSpecial")),
    ("WoodChest",      re.compile(r"Props_WoodChest")),
    ("SimpleChest",    re.compile(r"Props_SimpleChest")),
    ("Chest",          re.compile(r"Props_Chest|Props_FlatChest")),
    ("Coffin",         re.compile(r"Props_(?:Mermaid)?Coffin")),
    ("Equipment",      re.compile(r"LootDrop_Armor|LootDrop_Weapon")),
    ("Consumable",     re.compile(r"LootDrop_Potion|LootDrop_Bandage|LootDrop_LockPick")),
    ("Valuable",       re.compile(r"LootDrop_Coin|LootDrop_Gems|LootDrop_Trinkets|LootDrop_Ground|LootDrop_Bookshelf")),
    ("Herb",           re.compile(r"Props_PhantomFlower|Props_BlackRose|Props_Mushroom|Props_Saltvine|Props_IceCrystal|Props_Lifeleaf|Props_LavaMushroom|Props_Wardweed", re.I)),
    ("Ore",            re.compile(r"Props_(?:Ore|Mine|CopperOre|GoldOre|IronOre|RubyOre)", re.I)),
    ("SeaCreature",    re.compile(r"Props_GiantClam|Props_GiantBarnacle")),
    ("QuestItem",      re.compile(r"^Id_Spawner_Lootdrop_")),
    ("Trap",           re.compile(r"Props_FloorSpikes|Props_WallSpike|Props_TrackAxe|Props_PressurePlate|Props_SwingingAxe|Props_FireBreath|Props_LavaTrap|Props_ExplosionTrap")),
    ("Portal",         re.compile(r"Props_FloorPortal|Props_Escape")),
    ("Interact",       re.compile(r"Props_.*Lever|Props_.*Door|Props_Portcullis|Props_AltarOfSacrifice|Props_CaveSecretWall|Props_CryptSecret|Props_.*Secret|Props_.*Shrine", re.I)),
    ("Container",      re.compile(r"Props_WoodenBarrel|Props_WoodenCrate|Props_Pot\d|Props_SpiderPot|Props_Skeleton(?:Corpse|Bones|WoodenBarrel)")),
]

# Skip non-gameplay categories
SKIP_CATEGORIES = {"PlayerSpawn", "Trap", "Portal", "Interact", "NPC"}

# Decoration filter
DECO_RE = re.compile(r"Props_(?:Torch|Roaster|Candle|BoldTorch|SkullTorch|Statue|StoneTomb|Bonfire|Campfire|Lamp|Lantern|FirePit|ModuleConnector|CryptModuleConnector|.*Connector)", re.I)


def categorize(sid: str) -> str | None:
    """Classify a spawner ID into a category."""
    if sid == "PlayerSpawn":
        return "PlayerSpawn"
    for cat, pattern in CATEGORY_PATTERNS:
        if pattern.search(sid):
            return cat
    return None


def clean_source_name(sid: str) -> str:
    """Clean spawner ID into display name."""
    name = sid
    name = re.sub(r"^Id_Spawner_(?:New_)?", "", name)
    name = re.sub(r"^(?:Props|Monster|NPC|LootDrop|Lootdrop)_", "", name)
    name = re.sub(r"^(?:Ore|Spawn)_", "", name)
    name = re.sub(r"_On$", "", name)
    name = re.sub(r"\d{2,}(?:_\d+)*", "", name)
    name = name.replace("_", " ")
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    return name.strip()


def clean_variant_name(vid: str) -> str:
    """Clean props/monster ID into variant display name."""
    if not vid:
        return ""
    name = re.sub(r"^Id_(?:Props|Monster|LootDropGroup|LootdropGroup)_", "", name := vid, flags=re.I)
    name = name.replace("_", " ")
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    return name.strip()


def clean_pool_name(drop_id: str) -> str:
    """Clean LootDrop ID into pool display name."""
    name = re.sub(r"^ID_Lootdrop_(?:Drop_|Spawn_)?", "", drop_id, flags=re.I)
    # Common mapping
    mapping = {
        r"^Treasure": "Treasure", r"^Trinkets": "Trinkets", r"^Gems": "Gems",
        r"^EventCurrency": "Event Currency", r"^GoldCoin": "Gold Coins",
        r"^CorrodedKey": "Corroded Key", r"^Bandage": "Bandage",
        r"^Ale": "Ale", r"^Arrow": "Arrow",
    }
    for pat, repl in mapping.items():
        if re.match(pat, name, re.I):
            return repl
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    name = name.replace("_", " ").strip()
    return name


# ---------------------------------------------------------------------------
# Item name processing
# ---------------------------------------------------------------------------

_RARITY_SUFFIX_RE = re.compile(r"_(\d{4})$")


def item_asset_name(item_id: str) -> str:
    """Strip Id_Item_ prefix and _XXXX rarity suffix, keep CamelCase."""
    name = re.sub(r"^Id_Item_", "", item_id, flags=re.I)
    name = _RARITY_SUFFIX_RE.sub("", name)
    return name


def clean_item_name(item_id: str) -> str:
    """Strip Id_Item_ prefix and _XXXX rarity suffix, convert to readable name."""
    name = item_asset_name(item_id)
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    name = name.replace("_", " ").strip()
    return name


def has_rarity_suffix(item_id: str) -> bool:
    return bool(_RARITY_SUFFIX_RE.search(item_id))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Spawner placement — read raw UE map files
# ---------------------------------------------------------------------------

_SPAWNER_ID_RE = re.compile(r"'([^']+)'")
_SKIP_STEMS = ("Arena_D", "Arena_S", "_Env", "LevelSequence")


def build_spawner_dungeon_map(raw_maps_dir: Path) -> tuple[dict[str, set[str]], dict[str, dict[str, set[str]]]]:
    """Read BP_GameSpawner_C actors from raw UE level files.
    Returns:
        dungeon_map:  spawner_id → set of dungeon names
        module_map:   spawner_id → {dungeon_name → set of module names}
    The module map is scoped per-dungeon so that shared spawners don't leak
    modules from other dungeons."""
    dungeon_map: dict[str, set[str]] = defaultdict(set)
    module_map: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for dir_name, dungeon_name in MAP_DIR_TO_DUNGEON.items():
        dir_path = raw_maps_dir / dir_name
        if not dir_path.exists():
            continue
        for f in dir_path.rglob("*.json"):
            if any(skip in f.stem for skip in _SKIP_STEMS):
                continue
            # Module name: parent directory of the JSON file
            # e.g. .../Crypt/Center/AltarRoomAB/Crypt_AltarRoomAB_S.json → "AltarRoomAB"
            module_name = f.parent.name
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(data, list):
                continue
            for obj in data:
                if not isinstance(obj, dict) or obj.get("Type") != "BP_GameSpawner_C":
                    continue
                obj_name = obj.get("Properties", {}).get("SpawnerDataAsset", {}).get("ObjectName", "")
                m = _SPAWNER_ID_RE.search(obj_name)
                if m:
                    sid = m.group(1)
                    dungeon_map[sid].add(dungeon_name)
                    module_map[sid][dungeon_name].add(module_name)
    return dict(dungeon_map), dict(module_map)


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def load_spawners(spawns_dir: Path) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    for f in spawns_dir.glob("Id_Spawner_*.json"):
        d = _load(f)
        result[d["id"]] = d.get("spawner_items", [])
    return result


def load_loot_drop_groups(spawns_dir: Path) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    for prefix in ("ID_LootDropGroup_", "Id_LootDropGroup_", "ID_LootdropGroup_", "Id_LootdropGroup_"):
        for f in spawns_dir.glob(f"{prefix}*.json"):
            d = _load(f)
            result[d["id"]] = d.get("items", [])
    return result


def load_loot_drops(spawns_dir: Path) -> dict[str, list[dict]]:
    """loot_drop_id → [{item_id, item_count, luck_grade}]."""
    result: dict[str, list[dict]] = {}
    for prefix in ("ID_Lootdrop_", "Id_Lootdrop_"):
        for f in spawns_dir.glob(f"{prefix}*.json"):
            d = _load(f)
            result[d["id"]] = d.get("items", [])
    return result


def load_loot_drop_rates(spawns_dir: Path) -> dict[str, list[dict]]:
    """rate_id → [{luck_grade, drop_rate}]."""
    result: dict[str, list[dict]] = {}
    for pattern in ("ID_Droprate_*.json", "Id_Droprate_*.json"):
        for f in spawns_dir.glob(pattern):
            d = _load(f)
            result[d["id"]] = d.get("rates", [])
    return result


def load_items(items_dir: Path) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for f in items_dir.glob("Id_Item_*.json"):
        d = _load(f)
        result[d["id"]] = d
    return result


def load_monster_names(monsters_dir: Path) -> dict[str, str]:
    """Load display names from extracted monster files. Returns monster_id → display name."""
    result: dict[str, str] = {}
    for f in monsters_dir.glob("Id_Monster_*.json"):
        try:
            d = _load(f)
            name = d.get("name", "")
            if name:
                result[d["id"]] = name
        except Exception:
            continue
    return result


def load_module_display_names(dungeons_dir: Path) -> dict[str, str]:
    """Load display names from extracted dungeon module files.
    Returns directory_name → display name (e.g. 'CaveTown_02' → 'Goblin Town B').

    Creates multiple lookup keys per module to handle naming mismatches between
    raw map directory names and extracted module IDs.  For example, raw dirs use
    'MagmaFalls' but the extracted ID is 'Firedeep_MagmaFalls'.
    """
    # Dungeon prefixes used in extracted module IDs but absent from some raw
    # directory names.  Order matters: longer prefixes first to avoid partial
    # matches (e.g. 'IceCave' before 'Ice').
    _DUNGEON_PREFIXES = sorted(MAP_DIR_TO_DUNGEON.keys(), key=len, reverse=True)

    result: dict[str, str] = {}
    for f in dungeons_dir.glob("Id_DungeonModule_*.json"):
        try:
            d = _load(f)
            name = d.get("name", "")
            if name:
                # Full key  e.g. "Firedeep_MagmaFalls"
                dir_name = d["id"].replace("Id_DungeonModule_", "")
                result[dir_name] = name

                # Also register with dungeon prefix stripped so raw dir names
                # like "MagmaFalls" or "AltarRoomAB" resolve correctly.
                for prefix in _DUNGEON_PREFIXES:
                    # Try "Prefix_Rest" (underscore separator)
                    if dir_name.startswith(prefix + "_") and len(dir_name) > len(prefix) + 1:
                        short = dir_name[len(prefix) + 1:]
                        result.setdefault(short, name)
                        break
                    # Try "PrefixRest" (no separator, e.g. CryptAltarRoomAB)
                    if dir_name.startswith(prefix) and len(dir_name) > len(prefix):
                        short = dir_name[len(prefix):]
                        # Only accept if the remainder starts with uppercase
                        # (avoids false positives like "Caveltar" matching "Cave")
                        if short[0].isupper():
                            result.setdefault(short, name)
                            break
        except Exception:
            continue
    return result


def load_props_names(props_dir: Path) -> dict[str, str]:
    """Load display names from V2 Props files. Returns props_id → display name."""
    result: dict[str, str] = {}
    if not props_dir.exists():
        return result
    for f in props_dir.glob("Id_Props_*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            props = data[0]["Properties"] if isinstance(data, list) else data.get("Properties", {})
            name_obj = props.get("Name", {})
            name = name_obj.get("LocalizedString", "") if isinstance(name_obj, dict) else ""
            if name:
                result[f.stem] = name
        except Exception:
            continue
    return result


def load_interaction_counts(props_dir: Path) -> dict[str, int]:
    """Load InteractionMinCount from V2 Props files. Returns props_id → count."""
    result: dict[str, int] = {}
    if not props_dir.exists():
        return result
    for f in props_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            props = data[0]["Properties"] if isinstance(data, list) else data.get("Properties", {})
            ic = props.get("InteractionMinCount", 0)
            if ic and ic > 1:
                result[f.stem] = ic
        except Exception:
            continue
    return result


def build_icon_index(icon_dir: Path) -> dict[str, str]:
    """Build base_asset_name → best icon filename (without extension).
    Prefers _0001 variant, then lowest available suffix, then bare name."""
    if not icon_dir.exists():
        return {}
    by_base: dict[str, list[str]] = defaultdict(list)
    for f in icon_dir.iterdir():
        if not f.suffix == ".png":
            continue
        name = f.stem  # e.g. Item_Icon_Spear_0001
        if name.endswith("_RS") or "LowViolence" in name:
            continue
        # Strip Item_Icon_ prefix
        asset = name.replace("Item_Icon_", "")
        base = _RARITY_SUFFIX_RE.sub("", asset)
        by_base[base].append(asset)

    result: dict[str, str] = {}
    for base, variants in by_base.items():
        # Prefer _0001 (base icon), then bare name, then lowest suffix
        best = base  # fallback to bare name
        for v in sorted(variants):
            if v == base:
                best = base
                break
            if v.endswith("_0001"):
                best = v
                break
            best = v  # first sorted = lowest suffix
            break
        result[base] = f"Item_Icon_{best}"
    return result


# ---------------------------------------------------------------------------
# Grade=0 fallback for LootDropGroup entries
# ---------------------------------------------------------------------------

def get_group_entries(group_items: list[dict], grade: int) -> list[dict]:
    specific = [e for e in group_items if e.get("dungeon_grade", 0) == grade]
    if specific:
        return specific
    return [e for e in group_items if e.get("dungeon_grade", 0) == 0]


# ---------------------------------------------------------------------------
# Global data structures (indexed arrays like reference project)
# ---------------------------------------------------------------------------

class DataBuilder:
    def __init__(self):
        self.items: list[str] = []           # index → cleaned base name
        self.item_idx: dict[str, int] = {}   # name → index
        self.item_asset: dict[int, str] = {} # idx → CamelCase asset name
        self.item_meta: dict[int, dict] = {} # idx → {type, slot, armor, display_name}

        self.pools: list[dict] = []          # index → {name, lg_items: {lg: [itemIdx,...]}}
        self.pool_dedup: dict[str, int] = {} # dedup key → poolIdx

        self.rates: list[list[int]] = []     # index → [9 values]
        self.rate_dedup: dict[str, int] = {} # dedup key → rateIdx

        self.sources: list[dict] = []        # all source entries
        self.fixed_rarity: dict[int, int] = {} # itemIdx → rarity int (for items without _XXXX suffix)

    def get_item_idx(self, base_name: str) -> int:
        if base_name in self.item_idx:
            return self.item_idx[base_name]
        idx = len(self.items)
        self.items.append(base_name)
        self.item_idx[base_name] = idx
        return idx

    def process_pool(self, drop_id: str, loot_drops: dict[str, list[dict]]) -> int | None:
        """Process a LootDrop into a pool. Returns poolIdx."""
        entries = loot_drops.get(drop_id)
        if not entries:
            return None

        # Group items by luck grade
        by_lg: dict[int, dict[str, bool]] = defaultdict(dict)
        for entry in entries:
            item_id = entry.get("item_id")
            if not item_id:
                continue
            base = clean_item_name(item_id)
            if not base:
                continue
            lg = entry.get("luck_grade", 0)
            by_lg[lg][base] = True

            # Track asset name (CamelCase) for icon lookup
            idx = self.get_item_idx(base)
            if idx not in self.item_asset:
                self.item_asset[idx] = item_asset_name(item_id)

            # Track fixed-rarity items (no _XXXX suffix)
            if not has_rarity_suffix(item_id):
                if idx not in self.fixed_rarity:
                    self.fixed_rarity[idx] = 0  # placeholder, fill later

        # Build dedup key
        name = clean_pool_name(drop_id)
        key_parts = []
        lg_items: dict[int, list[int]] = {}
        for lg in sorted(by_lg.keys()):
            sorted_names = sorted(by_lg[lg].keys())
            idxs = [self.get_item_idx(n) for n in sorted_names]
            lg_items[lg] = idxs
            key_parts.append(f"{lg}:{','.join(str(i) for i in idxs)}")

        key = f"{name}|{'|'.join(key_parts)}"
        if key in self.pool_dedup:
            return self.pool_dedup[key]

        pool_idx = len(self.pools)
        self.pool_dedup[key] = pool_idx
        self.pools.append({"name": name, "lg_items": lg_items})
        return pool_idx

    def process_rate(self, rate_id: str, loot_drop_rates: dict[str, list[dict]]) -> int | None:
        """Process a LootDropRate into a rate array. Returns rateIdx."""
        entries = loot_drop_rates.get(rate_id)
        if not entries:
            return None

        rates = [0] * 9
        for entry in entries:
            lg = entry.get("luck_grade", 0)
            if 0 <= lg <= 8:
                rates[lg] = entry.get("drop_rate", 0)

        key = ",".join(str(r) for r in rates)
        if key in self.rate_dedup:
            return self.rate_dedup[key]

        rate_idx = len(self.rates)
        self.rate_dedup[key] = rate_idx
        self.rates.append(rates)
        return rate_idx

    def process_group(self, group_id: str, grade: int,
                      loot_drop_groups: dict[str, list[dict]],
                      loot_drops: dict[str, list[dict]],
                      loot_drop_rates: dict[str, list[dict]]) -> list[list[int]] | None:
        """Process a LootDropGroup for a specific grade.
        Returns [[poolIdx, rateIdx, count], ...] or None."""
        group_items = loot_drop_groups.get(group_id)
        if not group_items:
            return None

        entries = get_group_entries(group_items, grade)
        if not entries:
            return None

        pool_refs: list[list[int]] = []
        for entry in entries:
            drop_id = entry.get("loot_drop_id")
            rate_id = entry.get("loot_drop_rate_id")
            count = entry.get("loot_drop_count", 1)
            if not drop_id or not rate_id or count <= 0:
                continue

            pi = self.process_pool(drop_id, loot_drops)
            ri = self.process_rate(rate_id, loot_drop_rates)
            if pi is None or ri is None:
                continue
            pool_refs.append([pi, ri, count])

        return pool_refs if pool_refs else None


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build item search JSON for the wiki website.")
    p.add_argument("--extracted", default=str(EXTRACTED), help="Path to extracted/ directory")
    p.add_argument("--raw", default=str(RAW_MAPS_DIR), help="Path to raw UE Maps/Dungeon/Modules directory")
    p.add_argument("--out", default=str(OUT_FILE), help="Output JSON path")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    extracted = Path(args.extracted)
    raw_maps_dir = Path(args.raw)
    out_path = Path(args.out)

    print("Building item finder data...")
    spawns_dir = extracted / "spawns"
    items_dir = extracted / "items"
    props_dir = Path(args.props) if hasattr(args, 'props') else PROPS_V2_DIR
    icon_dir = ICON_DIR

    # Load all data
    print("  Building spawner placement map...")
    spawner_dungeon_map, spawner_module_map = build_spawner_dungeon_map(raw_maps_dir)
    print(f"    {len(spawner_dungeon_map)} spawners mapped to dungeons")
    print(f"    {len(spawner_module_map)} spawners mapped to modules (per-dungeon)")

    print("  Loading data...")
    spawners = load_spawners(spawns_dir)
    loot_drop_groups = load_loot_drop_groups(spawns_dir)
    loot_drops = load_loot_drops(spawns_dir)
    loot_drop_rates = load_loot_drop_rates(spawns_dir)
    items_data = load_items(items_dir)
    interaction_counts = load_interaction_counts(props_dir)
    monster_names = load_monster_names(extracted / "monsters")
    module_display_names = load_module_display_names(extracted / "dungeons")
    props_names = load_props_names(props_dir)
    icon_index = build_icon_index(icon_dir)
    print(f"    {len(spawners)} spawners, {len(loot_drop_groups)} groups, "
          f"{len(loot_drops)} drops, {len(loot_drop_rates)} rates, {len(items_data)} items")
    print(f"    {len(interaction_counts)} props with interaction counts, {len(icon_index)} icon bases")
    print(f"    {len(monster_names)} monster names, {len(module_display_names)} module names, {len(props_names)} props names")

    # Build
    db = DataBuilder()

    for di, dung in enumerate(DUNGEONS):
        dung_name = dung["name"]
        # Find spawners placed in this dungeon
        dungeon_spawners = {
            sid: spawners[sid]
            for sid in spawners
            if dung_name in spawner_dungeon_map.get(sid, set())
        }

        for grade_int, grade_label in dung["grades"]:
            source_count = 0

            for sid, spawner_items in sorted(dungeon_spawners.items()):
                if not spawner_items:
                    continue

                # Skip decorations and non-gameplay
                if DECO_RE.search(sid):
                    continue
                cat = categorize(sid)
                if not cat or cat in SKIP_CATEGORIES:
                    continue

                # Grade filter mode
                has_grade_filter = any(
                    bool(si.get("dungeon_grades"))
                    for si in spawner_items
                )

                # Build variant groups
                variant_groups: list[list] = []
                total_spawn_rate = 0
                seen_entry: set[str] = set()

                for si in spawner_items:
                    if has_grade_filter:
                        sp_grades = si.get("dungeon_grades", [])
                        if sp_grades:
                            if grade_int not in sp_grades:
                                continue
                        else:
                            continue  # no grades in filter mode = skip

                    spawn_rate = si.get("spawn_rate", 0)

                    group_id = si.get("loot_drop_group_id")
                    props_id = si.get("props_id") or ""
                    monster_id = si.get("monster_id") or ""

                    # Deduplicate identical entries
                    dedup_key = f"{spawn_rate}|{group_id}|{props_id}|{monster_id}"
                    if dedup_key in seen_entry:
                        continue
                    seen_entry.add(dedup_key)

                    total_spawn_rate += spawn_rate
                    if spawn_rate == 0 or not group_id:
                        continue

                    vname = ""
                    interact_count = 0
                    if props_id:
                        # Use V2 props display name if available
                        vname = props_names.get(props_id, "") or clean_variant_name(props_id)
                        interact_count = interaction_counts.get(props_id, 0)
                    elif monster_id:
                        # Use extracted monster display name
                        base_name = monster_names.get(monster_id, "")
                        if base_name:
                            # Extract tier from monster_id (Common/Elite/Nightmare)
                            tier_match = re.search(r"_(Common|Elite|Nightmare)$", monster_id)
                            tier = tier_match.group(1) if tier_match else ""
                            # Variant name includes monster name + tier for clarity
                            vname = f"{base_name} ({tier})" if tier else base_name
                        else:
                            vname = clean_variant_name(monster_id)

                    pool_refs = db.process_group(
                        group_id, grade_int,
                        loot_drop_groups, loot_drops, loot_drop_rates
                    )
                    if not pool_refs:
                        continue

                    variant_groups.append([spawn_rate, vname, pool_refs, interact_count])

                if not variant_groups:
                    continue

                # Derive best source display name from spawner items
                source_display = ""
                for si in spawner_items:
                    mid = si.get("monster_id") or ""
                    pid = si.get("props_id") or ""
                    if mid and mid in monster_names:
                        source_display = monster_names[mid]
                        break
                    if pid and pid in props_names:
                        source_display = props_names[pid]
                        break
                if not source_display:
                    source_display = clean_source_name(sid)

                # Get modules this spawner appears in — scoped to current dungeon
                modules = sorted(spawner_module_map.get(sid, {}).get(dung_name, set()))
                db.sources.append({
                    "d": di,
                    "g": grade_int,
                    "n": source_display,
                    "c": cat,
                    "tr": total_spawn_rate,
                    "v": variant_groups,
                    "m": modules,
                })
                source_count += 1

            print(f"    {dung_name} / {grade_label} (grade {grade_int}): {source_count} sources")

    # Build inverted index: itemIdx → [[poolIdx, lg, countAtLG], ...]
    item_pools: dict[int, list[list[int]]] = defaultdict(list)
    for pi, pool in enumerate(db.pools):
        for lg_str, item_idxs in pool["lg_items"].items():
            lg = int(lg_str) if isinstance(lg_str, str) else lg_str
            count_at_lg = len(item_idxs)
            for ii in item_idxs:
                item_pools[ii].append([pi, lg, count_at_lg])

    # Fill fixed rarity from item data
    for raw_id, item_data in items_data.items():
        if has_rarity_suffix(raw_id):
            continue
        base = clean_item_name(raw_id)
        idx = db.item_idx.get(base)
        if idx is None:
            continue
        rarity_tag = item_data.get("rarity_type", "")
        rarity_int = RARITY_FROM_TAG.get(rarity_tag, 0)
        if rarity_int > 0:
            db.fixed_rarity[idx] = rarity_int

    # Build item metadata from item data files
    for raw_id, item_data in items_data.items():
        base = clean_item_name(raw_id)
        idx = db.item_idx.get(base)
        if idx is None or idx in db.item_meta:
            continue
        slot_raw = item_data.get("slot_type", "")
        armor_raw = item_data.get("armor_type", "")
        db.item_meta[idx] = {
            "dn": item_data.get("name", base),  # display name
            "it": item_data.get("item_type", ""),
            "st": slot_raw.split(".")[-1] if slot_raw else "",
            "at": armor_raw.split(".")[-1] if armor_raw else "",
        }

    # Build module index: deduplicate module names across all sources
    all_modules: set[str] = set()
    for s in db.sources:
        all_modules.update(s["m"])
    module_list = sorted(all_modules)
    # Build display name list parallel to module_list.
    # For modules without an extracted display name, generate one by stripping
    # dungeon directory prefixes and formatting the remainder.
    _PREFIX_ORDER = sorted(MAP_DIR_TO_DUNGEON.keys(), key=len, reverse=True)

    def _fallback_display(raw: str) -> str:
        """Strip dungeon prefix + format CamelCase/underscores into readable name."""
        name = raw
        for pfx in _PREFIX_ORDER:
            if name.startswith(pfx + "_") and len(name) > len(pfx) + 1:
                name = name[len(pfx) + 1:]
                break
            if name.startswith(pfx) and len(name) > len(pfx) and name[len(pfx)].isupper():
                name = name[len(pfx):]
                break
        # Strip trailing _NN number suffixes (e.g. _01, _02)
        name = re.sub(r"_(\d+)$", r" \1", name)
        # CamelCase → spaces
        name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
        name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", name)
        name = name.replace("_", " ").strip()
        # Remove trailing lone numbers like " 01" → ""
        name = re.sub(r"\s+0*(\d+)$", lambda m: f" {m.group(1)}" if int(m.group(1)) > 1 else "", name)
        return name.strip()

    module_display_list = [
        module_display_names.get(m, "") or _fallback_display(m)
        for m in module_list
    ]
    module_idx = {name: i for i, name in enumerate(module_list)}
    # Replace module names with indices in sources
    for s in db.sources:
        s["m"] = sorted(module_idx[m] for m in s["m"])

    # Stats
    items_with_pools = sum(1 for ii in range(len(db.items)) if ii in item_pools)
    print(f"\n  Summary:")
    print(f"    Items: {len(db.items)} (with pools: {items_with_pools})")
    print(f"    Pools: {len(db.pools)}")
    print(f"    Rates: {len(db.rates)}")
    print(f"    Sources: {len(db.sources)}")
    print(f"    Fixed-rarity items: {len(db.fixed_rarity)}")

    # Build icon map: itemIdx → icon filename (without .png)
    # Use case-insensitive fallback since game data has inconsistent casing
    icon_index_lower = {k.lower(): v for k, v in icon_index.items()}
    item_icons: dict[str, str] = {}
    for idx, asset in db.item_asset.items():
        icon = icon_index.get(asset) or icon_index_lower.get(asset.lower())
        if icon:
            item_icons[str(idx)] = icon
    print(f"    Items with icons: {len(item_icons)}")

    # Build output
    print(f"    Modules: {len(module_list)}")

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dungeons": [{"n": d["name"], "g": [[g, l] for g, l in d["grades"]]} for d in DUNGEONS],
        "rarities": RARITIES,
        "luck_curve": LUCK_CURVE,
        "modules": module_list,
        "module_display": module_display_list,
        "items": db.items,
        "item_meta": {str(k): v for k, v in db.item_meta.items()},
        "item_icons": item_icons,
        "item_pools": {str(k): v for k, v in item_pools.items()},
        "pools": [{"n": p["name"], "g": {str(lg): idxs for lg, idxs in p["lg_items"].items()}} for p in db.pools],
        "rates": db.rates,
        "sources": [
            [s["d"], s["g"], s["n"], s["c"], s["tr"], s["v"], s["m"]]
            for s in db.sources
        ],
        "fixed_rarity": {str(k): v for k, v in db.fixed_rarity.items()},
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, separators=(",", ":"))

    size_kb = out_path.stat().st_size / 1024
    print(f"  Written to {out_path} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
