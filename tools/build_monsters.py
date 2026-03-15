"""
build_monsters.py - Compile all monster data into website/public/data/monsters.json

Reads from:
  - extracted/monsters/Id_Monster_*.json
  - raw/.../V2/Monster/Monster/Id_Monster_*.json
  - raw/.../V2/Monster/MonsterEffect/Id_MonsterEffect_*.json
  - raw/.../V2/Monster/MonsterAbility/Id_MonsterAbility_*.json
"""

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED_DIR = ROOT / "extracted" / "monsters"
RAW_MONSTER_DIR = ROOT / "raw" / "DungeonCrawler" / "Content" / "DungeonCrawler" / "Data" / "Generated" / "V2" / "Monster" / "Monster"
RAW_EFFECT_DIR = ROOT / "raw" / "DungeonCrawler" / "Content" / "DungeonCrawler" / "Data" / "Generated" / "V2" / "Monster" / "MonsterEffect"
RAW_ABILITY_DIR = ROOT / "raw" / "DungeonCrawler" / "Content" / "DungeonCrawler" / "Data" / "Generated" / "V2" / "Monster" / "MonsterAbility"
RAW_SPAWNER_DIR = ROOT / "raw" / "DungeonCrawler" / "Content" / "DungeonCrawler" / "Data" / "Generated" / "V2" / "Spawner" / "Spawner"
RAW_MAPS_DIR = ROOT / "raw" / "DungeonCrawler" / "Content" / "DungeonCrawler" / "Maps" / "Dungeon" / "Modules"
CHARACTERS_DIR = ROOT / "raw" / "DungeonCrawler" / "Content" / "DungeonCrawler" / "Characters" / "Monster"
RAW_STATUS_BASE = ROOT / "raw" / "DungeonCrawler" / "Content" / "DungeonCrawler" / "ActorStatus" / "Debuff" / "Monster"
RAW_ICON_DIR = ROOT / "raw" / "DungeonCrawler" / "Content" / "DungeonCrawler" / "UI" / "Resources" / "IconActorStatus"
STATUS_ICON_OUT = ROOT / "website" / "public" / "icons" / "status"
RAW_LOOTDROP_DIR = ROOT / "raw" / "DungeonCrawler" / "Content" / "DungeonCrawler" / "Data" / "Generated" / "V2" / "LootDrop"
RAW_ITEM_DIR = ROOT / "raw" / "DungeonCrawler" / "Content" / "DungeonCrawler" / "Data" / "Generated" / "V2" / "Item" / "Item"
EXTRACTED_AOE_DIR = ROOT / "extracted" / "combat"
EXTRACTED_DUNGEON_DIR = ROOT / "extracted" / "dungeons"
OUTPUT_FILE = ROOT / "website" / "public" / "data" / "monsters.json"

# Map directory names to dungeon display names
MAP_DIR_TO_DUNGEON = {
    "Cave": "Goblin Cave",
    "Crypt": "Crypt",
    "Firedeep": "Firedeep",
    "IceCave": "Ice Cavern",
    "IceAbyss": "Ice Abyss",
    "Inferno": "Inferno",
    "Ruins": "Ruins",
    "ShipGraveyard": "Ship Graveyard",
}

# Known grades in order
GRADES = ["Common", "Elite", "Nightmare"]

# Known typos in combo attack names -> corrected form
COMBO_TYPO_FIXES = {
    "TailSlah": "TailSlash",
    "BackSteb": "BackStep",
}

# Ability name segments to skip (non-attack abilities)
SKIP_ABILITY_KEYWORDS = [
    "Death", "RunState", "Inspecting", "Staggered", "Idle",
    "Burrow", "Swim", "Walk", "Phase", "Check", "Start", "End",
    "State", "Aggro",
]

# Stats to extract from MonsterEffect base files
STAT_KEYS = [
    "MaxHealthAdd", "PhysicalDamageWeapon", "MoveSpeedBase", "ActionSpeed",
    "StrengthBase", "VigorBase", "AgilityBase", "DexterityBase",
    "WillBase", "KnowledgeBase", "ResourcefulnessBase",
    "MagicResistance", "MagicalReduction",
    "FireMagicalReduction", "IceMagicalReduction", "LightMagicalReduction",
    "DarkMagicalReduction", "DivineMagicalReduction", "EvilMagicalReduction",
    "EarthMagicalReduction", "ProjectileReductionMod",
    "ImpactResistance", "MaxImpactEndurance",
]


def load_json(path: Path) -> dict | list | None:
    """Load a JSON file, returning None if it doesn't exist or is invalid."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return None


def extract_asset_name(asset_path: str) -> str:
    """Extract the asset name from an AssetPathName like '/Game/.../Foo.Foo'."""
    return asset_path.split("/")[-1].split(".")[0]


def strip_prefix(value: str, prefix_pattern: str = "") -> str:
    """Strip a dot-separated prefix, returning the last segment."""
    if "." in value:
        return value.rsplit(".", 1)[-1]
    return value


def name_to_slug(name: str) -> str:
    """Convert a display name to a URL-friendly slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def should_skip_ability(ability_name: str) -> bool:
    """Check if an ability name matches a non-attack pattern."""
    # Extract the part after the monster prefix
    for keyword in SKIP_ABILITY_KEYWORDS:
        # Match keyword as a whole segment (bounded by _ or end of string)
        if re.search(rf"(?:^|_){keyword}(?:_|$)", ability_name):
            return True
    return False


def clean_attack_name(ability_name: str, monster_base: str) -> str:
    """Clean an attack ability name into a human-readable format.

    Example: Id_MonsterAbility_Abomination_Attack_1_HeavySwing_Up -> 1 HeavySwing Up
             Id_MonsterAbility_SkeletonArcherAttack1 -> Attack1
    """
    # Strip the Id_MonsterAbility_ prefix
    name = ability_name
    if name.startswith("Id_MonsterAbility_"):
        name = name[len("Id_MonsterAbility_"):]

    # Strip monster base name prefix (with or without underscore)
    if name.startswith(monster_base + "_"):
        name = name[len(monster_base) + 1:]
    elif name.startswith(monster_base):
        name = name[len(monster_base):]

    # Also try stripping grade-prefixed names like SkeletonArcherElite -> strip that too
    for grade in GRADES:
        variant = monster_base + grade
        if name.startswith(variant + "_"):
            name = name[len(variant) + 1:]
        elif name.startswith(variant):
            name = name[len(variant):]

    # Strip leading "Attack_" prefix
    if name.startswith("Attack_"):
        name = name[len("Attack_"):]

    # Convert underscores to spaces
    name = name.replace("_", " ").strip()

    # If empty, use original
    if not name:
        name = ability_name.split("_")[-1]

    return name


def get_image_folder_from_actor_path(actor_path: str) -> str:
    """Extract the first-level subfolder under Characters/Monster/ from ActorClass.ObjectPath."""
    # Path like: DungeonCrawler/Content/DungeonCrawler/Characters/Monster/Skeleton/SkeletonArcher/...
    match = re.search(r"Characters/Monster/([^/]+)/", actor_path)
    if match:
        return match.group(1)
    return ""


def get_base_stats(effect_file: Path) -> dict:
    """Read base stats from a MonsterEffect file."""
    data = load_json(effect_file)
    if not data:
        return {}

    props = data[0].get("Properties", {}) if isinstance(data, list) else data.get("Properties", {})
    stats = {}
    for key in STAT_KEYS:
        stats[key] = props.get(key, 0)
    return stats


def get_attack_damage(effect_name: str) -> dict | None:
    """Read attack damage data from a MonsterEffect damage file."""
    effect_file = RAW_EFFECT_DIR / f"{effect_name}.json"
    data = load_json(effect_file)
    if not data:
        return None

    props = data[0].get("Properties", {}) if isinstance(data, list) else data.get("Properties", {})
    if "ExecDamageWeaponRatio" not in props and "ExecImpactPower" not in props:
        return None

    return {
        "damage_ratio": props.get("ExecDamageWeaponRatio", 0),
        "impact_power": props.get("ExecImpactPower", 0),
    }


def process_ability(ability_ref: str, monster_base: str) -> dict | None:
    """Process a single ability reference, returning attack info or None."""
    ability_name = extract_asset_name(ability_ref)

    # Strip prefix for checking
    check_name = ability_name
    if check_name.startswith("Id_MonsterAbility_"):
        check_name = check_name[len("Id_MonsterAbility_"):]

    # Skip non-attack abilities
    if should_skip_ability(check_name):
        return None

    # Read the ability file
    ability_file = RAW_ABILITY_DIR / f"{ability_name}.json"
    data = load_json(ability_file)
    if not data:
        return None

    props = data[0].get("Properties", {}) if isinstance(data, list) else data.get("Properties", {})
    effects = props.get("Effects", [])

    # Find the damage effect among the ability's effects
    # First try effects with "_Damage" in name, then fall back to any with damage data
    damage_info = None
    fallback_candidates = []
    for eff in effects:
        eff_name = extract_asset_name(eff.get("AssetPathName", ""))
        if "_Damage" in eff_name:
            damage_info = get_attack_damage(eff_name)
            if damage_info:
                break
        elif "Lib_State" not in eff_name:
            # Skip library/state effects, but keep monster-specific ones as fallback
            fallback_candidates.append(eff_name)

    if not damage_info:
        for eff_name in fallback_candidates:
            damage_info = get_attack_damage(eff_name)
            if damage_info:
                break

    if not damage_info:
        return None

    attack_name = clean_attack_name(ability_name, monster_base)
    return {
        "name": attack_name,
        "damage_ratio": damage_info["damage_ratio"],
        "impact_power": damage_info["impact_power"],
    }


def find_base_effect_file(raw_monster_data: dict) -> str | None:
    """Find the base stats effect file from a raw monster's Effects[] list.

    Iterates through all effects and returns the first one that actually
    contains stat data (MaxHealthAdd). Some monsters have tag-only effects
    like Id_MonsterEffect_BossRoom as Effects[0].
    """
    props = raw_monster_data[0].get("Properties", {}) if isinstance(raw_monster_data, list) else raw_monster_data.get("Properties", {})
    effects = props.get("Effects", [])
    for eff in effects:
        name = extract_asset_name(eff.get("AssetPathName", ""))
        if not name:
            continue
        effect_file = RAW_EFFECT_DIR / f"{name}.json"
        data = load_json(effect_file)
        if not data:
            continue
        eprops = data[0].get("Properties", {}) if isinstance(data, list) else data.get("Properties", {})
        # Check for any combat stat key (not just MaxHealthAdd — some monsters don't have HP)
        if any(k in eprops for k in STAT_KEYS):
            return name
    return None


def _load_module_display_names() -> dict[str, str]:
    """Load module directory name -> display name from extracted dungeon data."""
    names: dict[str, str] = {}
    if not EXTRACTED_DUNGEON_DIR.exists():
        return names
    for f in EXTRACTED_DUNGEON_DIR.glob("Id_DungeonModule_*.json"):
        data = load_json(f)
        if not data:
            continue
        module_id = data.get("id", "").replace("Id_DungeonModule_", "")
        display = data.get("name", "")
        if module_id and display:
            names[module_id.lower()] = display
    return names


def _resolve_module_name(module_dir: str, module_names: dict[str, str]) -> str:
    """Resolve a module directory name to its in-game display name."""
    key = module_dir.lower()
    if key in module_names:
        return module_names[key]

    # Try stripping _Center, _02, _01 suffixes
    base = re.sub(r"_(?:Center|Edge)(?:_\d+)?$", "", module_dir)
    base = re.sub(r"_\d+$", "", base)
    if base.lower() in module_names:
        return module_names[base.lower()]

    # Try stripping dungeon prefix (Cave_, Inferno_)
    for prefix in ("Cave_", "Inferno_", "IceCave_", "Ruins_", "Crypt_", "ShipGraveyard_"):
        if module_dir.startswith(prefix):
            stripped = module_dir[len(prefix):]
            if stripped.lower() in module_names:
                return module_names[stripped.lower()]

    # Fallback: clean up the directory name itself
    clean = module_dir
    for prefix in ("Cave_", "Inferno_", "IceCave_", "Ruins_", "Crypt_"):
        if clean.startswith(prefix):
            clean = clean[len(prefix):]
    clean = re.sub(r"_(?:Center|Edge)(?:_\d+)?$", "", clean)
    clean = re.sub(r"_\d+$", "", clean)
    clean = re.sub(r"([a-z])([A-Z])", r"\1 \2", clean)
    clean = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", clean)
    return clean.replace("_", " ").strip()


def build_monster_spawn_map() -> dict[str, set[tuple[str, str]]]:
    """Build a mapping of monster spawner name -> set of (dungeon, module) pairs.

    Scans all map module files for references to Id_Spawner_New_Monster_* assets.
    Module names are resolved to in-game display names from extracted dungeon data.
    """
    module_names = _load_module_display_names()
    result: dict[str, set[tuple[str, str]]] = {}
    for dir_name, dungeon_name in MAP_DIR_TO_DUNGEON.items():
        dungeon_path = RAW_MAPS_DIR / dir_name
        if not dungeon_path.exists():
            continue
        for json_file in dungeon_path.rglob("*.json"):
            try:
                with open(json_file, encoding="utf-8") as f:
                    text = f.read()
            except Exception:
                continue

            spawners = re.findall(r"Id_Spawner_New_Monster_(\w+)", text)
            if not spawners:
                continue

            # Determine module from file path: {Dungeon}/{Slot}/{ModuleDir}/...
            rel = json_file.relative_to(dungeon_path)
            parts = rel.parts
            module_dir = parts[1] if len(parts) > 2 else parts[0] if len(parts) > 1 else ""
            module_display = _resolve_module_name(module_dir, module_names) if module_dir else ""

            for spawner_name in spawners:
                result.setdefault(spawner_name, set()).add((dungeon_name, module_display))
    return result


def map_spawner_to_monster_id(spawner_name: str) -> str:
    """Map a spawner name like 'SkeletonFootmanFromFakeDeath' to a monster base name
    like 'SkeletonFootman' for matching with monster id_tags."""
    # Strip common suffixes that appear in spawner names but not monster names
    name = spawner_name
    # Remove grade suffixes
    for suffix in ["_Common", "_Elite", "_Nightmare"]:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    # Remove spawner-specific suffixes
    for suffix in ["FromFakeDeath", "FakeDeath", "_Random", "_Nightmare",
                    "_3type", "_5type", "_2type"]:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    return name


def combo_name_to_animation_id(name: str) -> str:
    """Convert a combo attack name (PascalCase with spaces) to a kebab-case animation ID.

    Examples:
        TailSlash High -> tail-slash-high
        ShortDash -> short-dash
        WaterArrow 1 -> water-arrow-1
        BackSteb -> backstep (after typo fix)
    """
    # Apply known typo fixes
    for typo, fix in COMBO_TYPO_FIXES.items():
        name = name.replace(typo, fix)

    # Split PascalCase: insert space before uppercase letters preceded by lowercase
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", name)

    # Convert to kebab-case
    return re.sub(r"\s+", "-", name.strip()).lower()


def extract_combos(abilities: list[str], monster_base: str) -> list[dict]:
    """Extract combo chain transitions from ability names.

    Abilities with '_From_' encode transitions: the part before '_From_' is the
    destination attack, the part after is the source. Returns a deduplicated list
    with animation_id fields for playback.
    """
    combos = []
    seen = set()
    for ability_ref in abilities:
        name = extract_asset_name(ability_ref)
        if name.startswith("Id_MonsterAbility_"):
            name = name[len("Id_MonsterAbility_"):]
        if name.startswith(monster_base + "_"):
            name = name[len(monster_base) + 1:]
        if name.startswith("Combo_"):
            name = name[len("Combo_"):]

        if "_From_" not in name:
            continue

        parts = name.split("_From_", 1)
        if len(parts) != 2:
            continue

        to_attack = parts[0].replace("_", " ").strip()
        from_attack = parts[1].replace("_", " ").strip()

        key = (from_attack, to_attack)
        if key not in seen:
            seen.add(key)
            combos.append({
                "from": from_attack,
                "to": to_attack,
                "from_animation_id": combo_name_to_animation_id(from_attack),
                "to_animation_id": combo_name_to_animation_id(to_attack),
            })

    return combos


def extract_status_effects(image_folder: str) -> tuple[list[dict], set[str]]:
    """Extract status effects from ActorStatus/Debuff/Monster/{folder}/.

    Returns (effects_list, set_of_icon_names_to_copy).
    """
    status_dir = RAW_STATUS_BASE / image_folder
    if not status_dir.exists():
        return [], set()

    effects = []
    icons_needed = set()

    for ge_file in sorted(status_dir.glob("GE_*.json")):
        data = load_json(ge_file)
        if not data:
            continue

        effect_name = ge_file.stem
        clean_name = effect_name
        if clean_name.startswith("GE_"):
            clean_name = clean_name[3:]
        if clean_name.startswith(image_folder + "_"):
            clean_name = clean_name[len(image_folder) + 1:]
        clean_name = clean_name.replace("_", " ")

        icon_name = ""
        tags = []
        for obj in data if isinstance(data, list) else [data]:
            obj_type = obj.get("Type", "")
            props = obj.get("Properties", {})

            if obj_type == "DCGameplayEffectUIData":
                ui_asset = props.get("UIDataAsset", {})
                obj_name = ui_asset.get("ObjectName", "")
                if "'" in obj_name:
                    ui_name = obj_name.split("'")[-2]
                    if ui_name:
                        ui_file = status_dir / f"{ui_name}.json"
                        ui_data = load_json(ui_file)
                        if ui_data:
                            for ui_obj in ui_data if isinstance(ui_data, list) else [ui_data]:
                                icon_tex = ui_obj.get("Properties", {}).get("IconTexture", {})
                                tex_name = icon_tex.get("ObjectName", "")
                                if "'" in tex_name:
                                    icon_name = tex_name.split("'")[-2]
                                    icons_needed.add(icon_name)

            if obj_type.startswith("GE_") or obj_type == effect_name + "_C":
                removal_tags = props.get("RemovalTagRequirements", {}).get("RequireTags", [])
                for tag in removal_tags:
                    parts = tag.split(".")
                    if len(parts) >= 3:
                        tags.append(parts[-1])

        effects.append({
            "name": clean_name,
            "icon": icon_name,
            "tags": tags,
        })

    return effects, icons_needed


def copy_status_icons(icons_needed: set[str]):
    """Copy referenced status effect icon PNGs to the public directory."""
    if not icons_needed:
        return
    STATUS_ICON_OUT.mkdir(parents=True, exist_ok=True)
    copied = 0
    for icon_name in sorted(icons_needed):
        src = RAW_ICON_DIR / f"{icon_name}.png"
        dst = STATUS_ICON_OUT / f"{icon_name}.png"
        if src.exists():
            shutil.copy2(src, dst)
            copied += 1
    print(f"  Copied {copied}/{len(icons_needed)} status effect icons")


def extract_loot_drops(base_name: str) -> list[dict]:
    """Extract loot drop info from LootDropGroup files.

    Reads DungeonGrade=0 entries (base drops shared across all dungeon grades).
    """
    group_file = RAW_LOOTDROP_DIR / "LootDropGroup" / f"ID_LootdropGroup_{base_name}.json"
    data = load_json(group_file)
    if not data:
        return []

    props = data[0].get("Properties", {}) if isinstance(data, list) else data.get("Properties", {})
    items = props.get("LootDropGroupItemArray", [])

    drops = []
    seen = set()
    for item in items:
        if item.get("DungeonGrade", -1) != 0:
            continue
        drop_path = item.get("LootDropId", {}).get("AssetPathName", "")
        drop_name = extract_asset_name(drop_path)
        count = item.get("LootDropCount", 1)

        if not drop_name or drop_name in seen or count <= 0:
            continue
        seen.add(drop_name)

        clean = drop_name
        for prefix in ["ID_Lootdrop_Drop_", "ID_Lootdrop_Spawn_"]:
            if clean.startswith(prefix):
                clean = clean[len(prefix):]
        clean = re.sub(r"([a-z])([A-Z])", r"\1 \2", clean)

        drops.append({"name": clean, "quantity": count})

    return drops


def build_hunting_loot_map() -> dict[str, dict]:
    """Build a map of monster base name (lowercase) -> hunting loot item data.

    Scans raw V2 item files for MiscType == Type.Item.Misc.HuntingLoot.
    """
    result = {}
    if not RAW_ITEM_DIR.exists():
        return result

    for item_file in RAW_ITEM_DIR.glob("Id_Item_*.json"):
        data = load_json(item_file)
        if not data:
            continue

        props = data[0].get("Properties", {}) if isinstance(data, list) else data.get("Properties", {})
        misc_type = props.get("MiscType", {})
        tag_name = misc_type.get("TagName", "") if isinstance(misc_type, dict) else str(misc_type)
        if "HuntingLoot" not in tag_name:
            continue

        item_id = item_file.stem
        name_obj = props.get("Name", {})
        item_name = name_obj.get("LocalizedString", "") if isinstance(name_obj, dict) else str(name_obj)
        flavor_obj = props.get("FlavorText", {})
        flavor = flavor_obj.get("LocalizedString", "") if isinstance(flavor_obj, dict) else str(flavor_obj)
        rarity_obj = props.get("RarityType", {})
        rarity_tag = rarity_obj.get("TagName", "") if isinstance(rarity_obj, dict) else str(rarity_obj)
        rarity = rarity_tag.rsplit(".", 1)[-1] if rarity_tag else ""

        base = item_id
        if base.startswith("Id_Item_"):
            base = base[len("Id_Item_"):]
        for suffix in ["Egg", "Fang", "Horn", "Claw", "Scale", "Eye", "Heart",
                        "Wing", "Tooth", "Bone", "Hide", "Pelt", "Tail", "Head",
                        "Skull", "Trophy", "Essence", "Core", "Gem", "Crystal",
                        "Feather", "Antenna", "Shell", "Husk", "Stinger",
                        "LootItem", "Loot"]:
            if base.endswith(suffix) and len(base) > len(suffix):
                base = base[:-len(suffix)]
                break

        result[base.lower()] = {
            "name": item_name,
            "rarity": rarity,
            "description": flavor,
        }

    return result


def extract_projectiles(image_folder: str) -> list[dict]:
    """Extract projectile types from blueprint files.

    Scans BP_*.json files that inherit from BP_ProjectileActor.
    """
    monster_dir = CHARACTERS_DIR / image_folder
    if not monster_dir.exists():
        return []

    projectiles = []
    seen = set()
    for bp_file in sorted(monster_dir.glob("BP_*.json")):
        data = load_json(bp_file)
        if not data:
            continue

        is_projectile = False
        for obj in data if isinstance(data, list) else [data]:
            super_ref = obj.get("Super", {})
            super_name = super_ref.get("ObjectName", "")
            if "ProjectileActor" in super_name:
                is_projectile = True
                break

        if not is_projectile:
            continue

        name = bp_file.stem
        clean = name
        if clean.startswith("BP_"):
            clean = clean[3:]
        if clean.startswith(image_folder + "_"):
            clean = clean[len(image_folder) + 1:]
        clean = clean.replace("_", " ")

        if clean not in seen:
            seen.add(clean)
            projectiles.append({"name": clean})

    return projectiles


# Property keys to skip when extracting blueprint behavior (UE5 internals, visuals)
_BP_SKIP_PREFIXES = ("bOverride_", "UberGraph", "DefaultSceneRoot", "Default__")
_BP_SKIP_CONTAINS = (
    "Material", "Mesh", "Montage", "Animation", "Particle", "Sound",
    "Niagara", "Widget", "Component", "Capsule", "Collision", "Scene",
    "Sprite", "Arrow", "Socket", "Slot", "Preview", "Debug",
)
_BP_SKIP_EXACT = {
    "BlueprintCreatedComponents", "BlueprintSystemVersion",
    "InternalVariableGuidMap", "bCanBeDamaged", "AutoPossessAI",
    "AutoReceiveInput", "PreviewFX",
}


def _extract_bt_name(ref: dict) -> str:
    """Extract behavior tree name from an ObjectName reference like
    "BehaviorTree'BT_GhostKing'"."""
    obj_name = ref.get("ObjectName", "")
    if "'" in obj_name:
        return obj_name.split("'")[1]
    return ""


def _extract_asset_ref(item: dict) -> str:
    """Extract asset name from a PrimaryAssetName dict."""
    return item.get("PrimaryAssetName", "")


def _should_skip_bp_key(key: str) -> bool:
    """Check if a blueprint property key is UE5 internal / non-gameplay."""
    if key in _BP_SKIP_EXACT:
        return True
    for prefix in _BP_SKIP_PREFIXES:
        if key.startswith(prefix):
            return True
    for substr in _BP_SKIP_CONTAINS:
        if substr in key:
            return True
    return False


def _is_engine_ref(value: dict) -> bool:
    """Check if a dict value is a reference to Engine/ or Script/ internals."""
    obj_path = value.get("ObjectPath", "")
    if obj_path.startswith("/Engine/") or obj_path.startswith("/Script/"):
        return True
    # MaterialInstance refs
    obj_name = value.get("ObjectName", "")
    if obj_name.startswith("MaterialInstance"):
        return True
    return False


def extract_blueprint_behavior(image_folder: str, base_name: str) -> dict:
    """Extract behavioral data from BP_ blueprint JSON files.

    Reads the Common/base blueprint for gameplay properties (cooldowns,
    HP thresholds, damage params, combat config) and the AIController
    for perception config (sight, hearing).
    """
    monster_dir = CHARACTERS_DIR / image_folder
    if not monster_dir.exists():
        return {}

    base_lower = base_name.lower()
    behavior = {}

    # --- Find and process the Common/base blueprint ---
    common_file = None
    for bp_file in sorted(monster_dir.rglob("BP_*.json")):
        stem = bp_file.stem
        # Match base_name at start of filename after "BP_" prefix
        after_bp = stem[3:] if stem.startswith("BP_") else stem
        after_bp_lower = after_bp.lower()
        if not after_bp_lower.startswith(base_lower):
            continue
        # Skip Elite, Nightmare, Projectile, AIController, Summoned variants
        if any(skip in stem for skip in ("Elite", "Nightmare", "AIControl",
                                          "Projectile", "Arrow", "Summoned",
                                          "SmallGhost", "Rock", "FakeDeath")):
            continue
        # Prefer exact match: BP_{base_name}_Common or BP_{base_name}
        after_base = after_bp[len(base_name):]
        if after_base in ("_Common", ""):
            common_file = bp_file
            break
        # Otherwise keep looking, but remember first match as fallback
        if common_file is None:
            common_file = bp_file

    if common_file:
        data = load_json(common_file)
        if data:
            objects = data if isinstance(data, list) else [data]

            # Find CDO (Name starts with "Default__")
            cdo_props = {}
            for obj in objects:
                if obj.get("Name", "").startswith("Default__"):
                    cdo_props = obj.get("Properties", {})
                    break

            # Extract behavior trees
            for bt_key in ("Custom Behavior Tree", "Combat BehaviorTree"):
                bt_ref = cdo_props.get(bt_key)
                if isinstance(bt_ref, dict) and "ObjectName" in bt_ref:
                    field = "behavior_tree" if "Custom" in bt_key else "combat_behavior_tree"
                    name = _extract_bt_name(bt_ref)
                    if name:
                        behavior[field] = name

            # Extract all gameplay properties
            properties = {}
            for key, value in cdo_props.items():
                if _should_skip_bp_key(key):
                    continue

                # Skip behavior tree refs (already extracted above)
                if key in ("Custom Behavior Tree", "Combat BehaviorTree"):
                    continue

                # Scalars: int, float, bool
                if isinstance(value, bool):
                    properties[key] = value
                elif isinstance(value, (int, float)):
                    properties[key] = value
                # Strings (enum values etc.)
                elif isinstance(value, str) and value:
                    properties[key] = value
                # Tag structs
                elif isinstance(value, dict) and "TagName" in value:
                    properties[key] = value["TagName"]
                # Asset path references
                elif isinstance(value, dict) and "AssetPathName" in value:
                    asset = extract_asset_name(value["AssetPathName"])
                    if asset:
                        properties[key] = asset
                # Skip engine/material refs
                elif isinstance(value, dict):
                    if _is_engine_ref(value):
                        continue
                    # Other dict values with ObjectName (non-BT refs)
                    if "ObjectName" in value:
                        obj_name = value["ObjectName"]
                        if "'" in obj_name:
                            extracted = obj_name.split("'")[1]
                            if extracted:
                                properties[key] = extracted
                # Lists
                elif isinstance(value, list) and value:
                    # Tag arrays
                    if isinstance(value[0], dict) and "TagName" in value[0]:
                        tags = [v["TagName"] for v in value if "TagName" in v]
                        if tags:
                            properties[key] = tags
                    # Asset ref arrays
                    elif isinstance(value[0], dict) and "PrimaryAssetName" in value[0]:
                        refs = [_extract_asset_ref(v) for v in value]
                        refs = [r for r in refs if r]
                        if refs:
                            properties[key] = refs
                    # Scalar arrays
                    elif isinstance(value[0], (int, float, str)):
                        properties[key] = value
                    # Enum/string arrays
                    elif isinstance(value[0], str):
                        properties[key] = value

            if properties:
                behavior["properties"] = properties

    # --- Find and process AIController ---
    ai_file = None
    for bp_file in sorted(monster_dir.rglob("BP_*AIController*.json")):
        stem = bp_file.stem
        after_bp = stem[3:] if stem.startswith("BP_") else stem
        after_bp_lower = after_bp.lower()
        if not after_bp_lower.startswith(base_lower):
            continue
        # Skip Summoned AIControllers
        if "summoned" in after_bp_lower:
            continue
        ai_file = bp_file
        break

    if ai_file:
        data = load_json(ai_file)
        if data:
            objects = data if isinstance(data, list) else [data]
            for obj in objects:
                obj_type = obj.get("Type", "")
                props = obj.get("Properties", {})
                if obj_type == "AISenseConfig_Sight":
                    if "SightRadius" in props:
                        behavior["sight_radius"] = props["SightRadius"]
                    if "LoseSightRadius" in props:
                        behavior["lose_sight_radius"] = props["LoseSightRadius"]
                    if "PeripheralVisionAngleDegrees" in props:
                        behavior["peripheral_vision_angle"] = props["PeripheralVisionAngleDegrees"]
                elif obj_type == "AISenseConfig_Hearing":
                    if "HearingRange" in props:
                        behavior["hearing_range"] = props["HearingRange"]

    return behavior


def extract_aoe(base_name: str) -> list[dict]:
    """Extract AoE definitions from extracted combat data."""
    if not EXTRACTED_AOE_DIR.exists():
        return []

    aoes = []
    for aoe_file in sorted(EXTRACTED_AOE_DIR.glob(f"Id_Aoe_{base_name}_*.json")):
        data = load_json(aoe_file)
        if not data:
            continue

        aoe_id = data.get("id", aoe_file.stem)
        clean = aoe_id
        if clean.startswith("Id_Aoe_"):
            clean = clean[7:]
        if clean.startswith(base_name + "_"):
            clean = clean[len(base_name) + 1:]
        clean = clean.replace("_", " ")

        aoes.append({"name": clean})

    return aoes


def main():
    print("Building monsters.json...")

    # Step 0: Build spawn location map (spawner_name -> set of dungeon names)
    print("  Building spawn location map from map modules...")
    spawner_dungeon_map = build_monster_spawn_map()
    print(f"  Found {len(spawner_dungeon_map)} unique monster spawners across dungeons")

    # Step 1: Load all extracted monster files and group by IdTag
    extracted_files = sorted(EXTRACTED_DIR.glob("Id_Monster_*.json"))
    print(f"  Found {len(extracted_files)} extracted monster files")

    # Group monsters by id_tag, filtering out special variants
    # (Summoned, FogMissile, BonePrison, Crystal, etc.)
    monster_groups: dict[str, list[dict]] = {}
    skipped_variants = 0
    for f in extracted_files:
        data = load_json(f)
        if not data:
            continue
        id_tag = data.get("id_tag", "")
        if not id_tag:
            continue

        monster_id = data.get("id", "")  # e.g., "Id_Monster_SkeletonArcher_Common"
        suffix = monster_id[len("Id_Monster_"):]  # e.g., "SkeletonArcher_Common"
        grade_str = data.get("grade_type", "").rsplit(".", 1)[-1] if data.get("grade_type") else ""

        # Strip the grade suffix to get the file's base name
        if grade_str and suffix.endswith(f"_{grade_str}"):
            file_base = suffix[: -(len(grade_str) + 1)]
        else:
            file_base = suffix

        # Convert id_tag base to underscore form for comparison
        tag_base = id_tag[len("Id.Monster."):].replace(".", "_")

        # Compare ignoring underscores
        if file_base.replace("_", "").lower() != tag_base.replace("_", "").lower():
            skipped_variants += 1
            continue

        monster_groups.setdefault(id_tag, []).append(data)

    print(f"  Found {len(monster_groups)} unique monster base types")
    print(f"  Skipped {skipped_variants} special variants (Summoned, etc.)")

    # Step 1b: Build hunting loot map
    hunting_loot_map = build_hunting_loot_map()
    print(f"  Found {len(hunting_loot_map)} hunting loot items")

    all_icons_needed: set[str] = set()

    # Step 2: Pre-count display names to identify duplicates
    name_counts: dict[str, int] = {}
    for id_tag, variants in monster_groups.items():
        display_name = variants[0].get("name", "")
        name_counts[display_name] = name_counts.get(display_name, 0) + 1

    # Step 3: Process each monster group
    monsters = []
    skipped = 0

    for id_tag, variants in sorted(monster_groups.items()):
        tag_after_prefix = id_tag[len("Id.Monster."):]
        base_name = tag_after_prefix.split(".")[0]

        first = variants[0]
        display_name = first.get("name", base_name)

        # Skip DesignData internal test monsters
        if display_name.startswith("DesignData"):
            skipped += 1
            continue
        class_type = first.get("class_type", "").rsplit(".", 1)[-1] if first.get("class_type") else "Normal"

        # Creature types
        creature_types = []
        for ct in first.get("character_types", []):
            parts = ct.split(".")
            if len(parts) >= 3:
                creature_types.append(parts[2])
            else:
                creature_types.append(parts[-1])
        seen = set()
        unique_types = []
        for ct in creature_types:
            if ct not in seen:
                seen.add(ct)
                unique_types.append(ct)
        creature_types = unique_types

        # For monsters with duplicate display names, add a qualifier from id_tag
        if name_counts.get(display_name, 1) > 1:
            full_tag = tag_after_prefix.replace(".", "")
            # Try stripping the display name to find the variant part
            display_compressed = display_name.replace(" ", "")
            if full_tag.lower().startswith(display_compressed.lower()) and len(full_tag) > len(display_compressed):
                variant_part = full_tag[len(display_compressed):]
            else:
                # Use full tag as variant (covers cross-named cases)
                variant_part = full_tag
            variant_part = re.sub(r"([a-z])([A-Z])", r"\1 \2", variant_part)
            variant_part = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", variant_part)
            variant_clean = variant_part.strip()
            # Don't repeat the name itself as qualifier (e.g., "Banshee (Banshee)")
            if variant_clean.lower() != display_name.replace(" ", "").lower() and variant_clean:
                display_name = f"{display_name} ({variant_clean})"
            else:
                # Use class_type as differentiator
                display_name = f"{display_name} ({class_type})"
            slug = name_to_slug(display_name)
        else:
            slug = name_to_slug(display_name)

        # Find image folder from ActorClass in raw monster file
        image_folder = ""
        raw_monster_file = RAW_MONSTER_DIR / f"{first['id']}.json"
        raw_data = load_json(raw_monster_file)
        if raw_data:
            props = raw_data[0].get("Properties", {}) if isinstance(raw_data, list) else raw_data.get("Properties", {})
            actor_class = props.get("ActorClass", {})
            actor_path = actor_class.get("ObjectPath", "")
            image_folder = get_image_folder_from_actor_path(actor_path)

        # Process grades
        grades = {}
        all_attacks = {}

        for variant in variants:
            grade_str = variant.get("grade_type", "").rsplit(".", 1)[-1] if variant.get("grade_type") else "Common"

            raw_file = RAW_MONSTER_DIR / f"{variant['id']}.json"
            raw_data = load_json(raw_file)

            stats = {}
            grade_combos = []
            grade_abilities = []
            if raw_data:
                effect_name = find_base_effect_file(raw_data)
                if effect_name:
                    effect_file = RAW_EFFECT_DIR / f"{effect_name}.json"
                    stats = get_base_stats(effect_file)

                props = raw_data[0].get("Properties", {}) if isinstance(raw_data, list) else raw_data.get("Properties", {})
                for ability_ref in props.get("Abilities", []):
                    asset_path = ability_ref.get("AssetPathName", "")
                    attack = process_ability(asset_path, base_name)
                    if attack and attack["name"] not in all_attacks:
                        all_attacks[attack["name"]] = attack

                # Extract combo chains from this grade's abilities
                ability_paths = [a.get("AssetPathName", "") for a in props.get("Abilities", [])]
                grade_combos = extract_combos(ability_paths, base_name)

                # Build clean abilities list for this grade
                for ability_ref in props.get("Abilities", []):
                    aname = extract_asset_name(ability_ref.get("AssetPathName", ""))
                    check = aname[len("Id_MonsterAbility_"):] if aname.startswith("Id_MonsterAbility_") else aname
                    if not should_skip_ability(check):
                        grade_abilities.append(clean_attack_name(aname, base_name))

            grades[grade_str] = {
                "adv_point": variant.get("adv_point", 0),
                "exp_point": variant.get("exp_point", 0),
                "stats": stats,
                "combos": grade_combos,
                "abilities": grade_abilities,
            }

        if not grades:
            skipped += 1
            continue

        # Find spawn locations for this monster
        # Try matching spawner names to this monster's base name
        dungeons: set[str] = set()
        spawn_locations: list[dict] = []
        seen_spawns: set[tuple[str, str]] = set()
        base_lower = base_name.lower()
        for spawner_name, location_set in spawner_dungeon_map.items():
            mapped = map_spawner_to_monster_id(spawner_name)
            if mapped.lower() == base_lower:
                for dungeon, module in location_set:
                    dungeons.add(dungeon)
                    key = (dungeon, module)
                    if key not in seen_spawns and module:
                        seen_spawns.add(key)
                        spawn_locations.append({"dungeon": dungeon, "module": module})
        spawn_locations.sort(key=lambda s: (s["dungeon"], s["module"]))

        # Extract extended data
        status_effects, icons = extract_status_effects(image_folder)
        all_icons_needed.update(icons)
        loot_drops = extract_loot_drops(base_name)
        hunting_loot = hunting_loot_map.get(base_name.lower())
        projectiles = extract_projectiles(image_folder)
        aoe = extract_aoe(base_name)
        behavior = extract_blueprint_behavior(image_folder, base_name)

        monster = {
            "slug": slug,
            "name": display_name,
            "class_type": class_type,
            "creature_types": creature_types,
            "image": image_folder,
            "dungeons": sorted(dungeons),
            "spawn_locations": spawn_locations,
            "grades": grades,
            "attacks": list(all_attacks.values()),
            "status_effects": status_effects,
            "loot": loot_drops,
            "hunting_loot": hunting_loot,
            "projectiles": projectiles,
            "aoe": aoe,
            "behavior": behavior,
        }
        monsters.append(monster)

    # Sort by name
    monsters.sort(key=lambda m: m["name"])

    # Copy status effect icons
    copy_status_icons(all_icons_needed)

    # Build output
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "monsters": monsters,
    }

    # Write output
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    # Summary
    total_grades = sum(len(m["grades"]) for m in monsters)
    total_attacks = sum(len(m["attacks"]) for m in monsters)
    with_spawns = sum(1 for m in monsters if m["dungeons"])
    zero_hp = sum(1 for m in monsters for g in m["grades"].values()
                  if g["stats"].get("MaxHealthAdd", 0) == 0)

    print(f"\nOutput: {OUTPUT_FILE}")
    print(f"  Monsters:  {len(monsters)}")
    print(f"  Grades:    {total_grades}")
    print(f"  Attacks:   {total_attacks}")
    print(f"  With spawn locations: {with_spawns}")
    print(f"  Zero-HP grades: {zero_hp}")
    print(f"  Skipped:   {skipped}")

    # Extended data summary
    with_effects = sum(1 for m in monsters if m.get("status_effects"))
    with_loot = sum(1 for m in monsters if m.get("loot"))
    with_hunting = sum(1 for m in monsters if m.get("hunting_loot"))
    with_projectiles = sum(1 for m in monsters if m.get("projectiles"))
    with_aoe = sum(1 for m in monsters if m.get("aoe"))
    total_combos = sum(len(g.get("combos", [])) for m in monsters for g in m["grades"].values())
    print(f"  Status effects: {with_effects} monsters")
    print(f"  Loot drops: {with_loot} monsters")
    print(f"  Hunting loot: {with_hunting} monsters")
    print(f"  Projectiles: {with_projectiles} monsters")
    print(f"  AoE: {with_aoe} monsters")
    with_behavior = sum(1 for m in monsters if m.get("behavior"))
    print(f"  Behavior data: {with_behavior} monsters")
    print(f"  Total combos: {total_combos}")
    print(f"  Status icons: {len(all_icons_needed)}")

    # Show class breakdown
    class_counts: dict[str, int] = {}
    for m in monsters:
        class_counts[m["class_type"]] = class_counts.get(m["class_type"], 0) + 1
    print(f"  Class types: {dict(sorted(class_counts.items()))}")


if __name__ == "__main__":
    main()
