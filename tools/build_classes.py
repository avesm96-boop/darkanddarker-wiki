"""
build_classes.py - Compile all class data into website/public/data/classes.json

Reads from:
  - extracted/classes/Id_PlayerCharacterEffect_[Class].json   (base stats)
  - raw/.../V2/PlayerCharacter/PlayerCharacter/Id_PlayerCharacter_[Class].json  (flavor text, default perks)
  - raw/.../Data/GameplayAbility/CT_*.json                    (curve tables for derived stats)
  - extracted/classes/Id_Perk_*.json                          (perks)
  - extracted/classes/Id_Skill_*.json                         (skills)
  - raw/.../V2/Spell/Spell/Id_Spell_*.json                   (spells)
  - extracted/classes/Id_ShapeShift_*.json                    (shapeshifts, Druid only)
  - raw/.../V2/Spell/SpellMergeGroup/Id_SpellMergeGroup.json  (spell merge recipes)
  - raw/.../Localization/Game/en/Game.json                    (localization strings)
  - website/public/data/item_classes.json                     (usable item counts)
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED_CLASSES = ROOT / "extracted" / "classes"
RAW = ROOT / "raw" / "DungeonCrawler" / "Content" / "DungeonCrawler"
RAW_V2 = RAW / "Data" / "Generated" / "V2"
CURVE_DIR = RAW / "Data" / "GameplayAbility"
LOC_FILE = ROOT / "raw" / "DungeonCrawler" / "Content" / "Localization" / "Game" / "en" / "Game.json"
ITEM_CLASSES_FILE = ROOT / "website" / "public" / "data" / "item_classes.json"
OUTPUT_FILE = ROOT / "website" / "public" / "data" / "classes.json"

CLASS_NAMES = [
    "Barbarian", "Bard", "Cleric", "Druid", "Fighter",
    "Ranger", "Rogue", "Sorcerer", "Warlock", "Wizard",
]

ROLES = {
    "Barbarian": "Melee",
    "Fighter": "Melee",
    "Ranger": "Melee",
    "Rogue": "Melee",
    "Wizard": "Caster",
    "Sorcerer": "Caster",
    "Cleric": "Caster",
    "Druid": "Caster",
    "Warlock": "Hybrid",
    "Bard": "Hybrid",
}


def load_json(path):
    """Load a JSON file, returning None on error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
        print(f"  WARNING: Could not load {path}: {e}")
        return None


def load_localization():
    """Load the DC namespace from the localization file."""
    data = load_json(LOC_FILE)
    if data is None:
        return {}
    return data.get("DC", {})


def load_curve_table(filename, row_name):
    """Load a curve table and return the keys for the given row."""
    data = load_json(CURVE_DIR / filename)
    if data is None:
        return []
    rows = data[0].get("Rows", {})
    row = rows.get(row_name)
    if row is None:
        print(f"  WARNING: Row '{row_name}' not found in {filename}")
        return []
    return row.get("Keys", [])


def lerp_curve(keys, x):
    """Linearly interpolate a curve table at value x, clamped to endpoints."""
    if not keys:
        return 0.0
    # Clamp to first/last key
    if x <= keys[0]["Time"]:
        return keys[0]["Value"]
    if x >= keys[-1]["Time"]:
        return keys[-1]["Value"]
    # Find bracketing keys
    for i in range(len(keys) - 1):
        t0, v0 = keys[i]["Time"], keys[i]["Value"]
        t1, v1 = keys[i + 1]["Time"], keys[i + 1]["Value"]
        if t0 <= x <= t1:
            if t1 == t0:
                return v0
            frac = (x - t0) / (t1 - t0)
            return v0 + frac * (v1 - v0)
    return keys[-1]["Value"]


def compute_derived_stats(base_stats):
    """Compute derived stats from base stats using curve tables."""
    vigor = base_stats["vigor"]
    knowledge = base_stats["knowledge"]
    will = base_stats["will"]
    agility = base_stats["agility"]
    dexterity = base_stats["dexterity"]
    strength = base_stats["strength"]
    resourcefulness = base_stats["resourcefulness"]

    # Load curve tables
    ct_health = load_curve_table("CT_MaxHealthBase.json", "MaxHealthBase")
    ct_mem_cap = load_curve_table("CT_Knowledge.json", "MemoryCapacity")
    ct_spell_speed = load_curve_table("CT_Knowledge.json", "SpellCastingSpeed")
    ct_magic_res = load_curve_table("CT_Will.json", "MagicResistance")
    ct_buff_dur = load_curve_table("CT_Will.json", "BuffDurationMod")
    ct_debuff_dur = load_curve_table("CT_Will.json", "DebuffDurationMod")
    ct_move_speed = load_curve_table("CT_Agility.json", "MoveSpeedBase")
    ct_action_speed = load_curve_table("CT_Agility.json", "ActionSpeed")
    ct_manual_dex = load_curve_table("CT_Dexterity.json", "ManualDexterity")
    ct_equip_speed = load_curve_table("CT_Dexterity.json", "ItemEquipSpeed")
    ct_phys_power = load_curve_table("CT_Strength.json", "PhysicalPower")
    ct_interact = load_curve_table("CT_RegularInteractionSpeedBase.json", "RegularInteractionSpeed")
    ct_recovery = load_curve_table("CT_RecoveryMod.json", "HealthRecoveryMod")

    health = lerp_curve(ct_health, vigor)
    move_speed_mod = lerp_curve(ct_move_speed, agility)
    move_speed = 300 + move_speed_mod

    return {
        "health": round(health, 1),
        "move_speed": round(move_speed, 1),
        "move_speed_pct": round(move_speed_mod / 3, 1),  # base is 300, so pct = mod/3
        "action_speed_pct": round(lerp_curve(ct_action_speed, agility) * 100, 1),
        "spell_casting_speed_pct": round(lerp_curve(ct_spell_speed, knowledge) * 100, 1),
        "memory_capacity": round(lerp_curve(ct_mem_cap, knowledge)),
        "magic_resistance_pct": round(lerp_curve(ct_magic_res, will), 1),
        "physical_power": round(lerp_curve(ct_phys_power, strength), 1),
        "manual_dexterity_pct": round(lerp_curve(ct_manual_dex, dexterity) * 100, 1),
        "equip_speed_pct": round(lerp_curve(ct_equip_speed, dexterity) * 100, 1),
        "buff_duration_pct": round(lerp_curve(ct_buff_dur, will) * 100, 1),
        "debuff_duration_pct": round(lerp_curve(ct_debuff_dur, will) * 100, 1),
        "regular_interaction_speed_pct": round(lerp_curve(ct_interact, resourcefulness) * 100, 1),
        "health_recovery_bonus_pct": round(lerp_curve(ct_recovery, resourcefulness) * 100, 1),
    }


def class_matches(classes_list, class_name):
    """Check if a class list contains the base or GrandMaster variant of a class."""
    base_id = f"Id_PlayerCharacter_{class_name}"
    gm_id = f"Id_PlayerCharacter_GrandMaster_{class_name}"
    for entry in classes_list:
        if isinstance(entry, str):
            if entry in (base_id, gm_id):
                return True
        elif isinstance(entry, dict):
            name = entry.get("PrimaryAssetName", "")
            if name in (base_id, gm_id):
                return True
    return False


def extract_id_name(full_id, prefix):
    """Extract the short name from a full ID like 'Id_Perk_SwordMastery' -> 'SwordMastery'."""
    if full_id.startswith(prefix):
        return full_id[len(prefix):]
    return full_id


def to_display_name(id_name):
    """Convert CamelCase ID to display name with spaces: 'SwordMastery' -> 'Sword Mastery'."""
    # Insert space before uppercase letters that follow lowercase letters
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", id_name)
    # Insert space before uppercase letters that are followed by lowercase and preceded by uppercase
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", name)
    return name


def to_slug(name):
    """Convert a display name to a URL slug."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def get_default_perk_ids(class_name):
    """Get the set of default perk IDs from the raw PlayerCharacter data."""
    path = RAW_V2 / "PlayerCharacter" / "PlayerCharacter" / f"Id_PlayerCharacter_{class_name}.json"
    data = load_json(path)
    if data is None:
        return set()
    props = data[0].get("Properties", {})
    perks = props.get("Perks", [])
    result = set()
    for perk in perks:
        asset_path = perk.get("AssetPathName", "")
        # Extract perk ID from path like ".../Id_Perk_SwordMastery.Id_Perk_SwordMastery"
        parts = asset_path.split(".")
        if parts:
            result.add(parts[-1])
    return result


def collect_perks(class_name, loc):
    """Collect all perks for a given class."""
    default_ids = get_default_perk_ids(class_name)
    perks = []
    for path in sorted(EXTRACTED_CLASSES.glob("Id_Perk_*.json")):
        data = load_json(path)
        if data is None:
            continue
        classes = data.get("classes", [])
        if not class_matches(classes, class_name):
            continue
        perk_id = data["id"]
        short_name = extract_id_name(perk_id, "Id_Perk_")
        display_name = data.get("name") or to_display_name(short_name)
        # Get description from localization
        desc_key = f"Text_DataAsset_{short_name}_Desc_{short_name}Desc"
        description = loc.get(desc_key, "")
        is_default = perk_id in default_ids
        perks.append({
            "id": short_name,
            "name": display_name,
            "description": description,
            "is_default": is_default,
        })
    return perks


def collect_skills(class_name, loc):
    """Collect all skills for a given class."""
    skills = []
    for path in sorted(EXTRACTED_CLASSES.glob("Id_Skill_*.json")):
        data = load_json(path)
        if data is None:
            continue
        classes = data.get("classes", [])
        if not class_matches(classes, class_name):
            continue
        skill_id = data["id"]
        short_name = extract_id_name(skill_id, "Id_Skill_")
        display_name = data.get("name") or to_display_name(short_name)
        # Get description from localization
        desc_key = f"Text_DataAsset_{short_name}_Desc_{short_name}Desc"
        description = loc.get(desc_key, "")
        # Extract skill_type last segment (e.g., "Type.Skill.Instant" -> "instant")
        raw_type = data.get("skill_type", "")
        skill_type = raw_type.split(".")[-1].lower() if raw_type else ""
        skills.append({
            "id": short_name,
            "name": display_name,
            "description": description,
            "skill_type": skill_type,
            "skill_tier": data.get("skill_tier", 1),
            "use_moving": data.get("use_moving", False),
        })
    return skills


def collect_spells(class_name, loc):
    """Collect all spells for a given class from raw spell files."""
    spells = []
    spell_dir = RAW_V2 / "Spell" / "Spell"
    if not spell_dir.exists():
        return spells
    for path in sorted(spell_dir.glob("Id_Spell_*.json")):
        data = load_json(path)
        if data is None:
            continue
        props = data[0].get("Properties", {})
        # Check class membership via PrimaryAssetName
        classes = props.get("Classes", [])
        if not class_matches(classes, class_name):
            continue
        spell_id = data[0].get("Name", "")
        short_name = extract_id_name(spell_id, "Id_Spell_")
        # Get display name from localization or Properties.Name
        name_obj = props.get("Name", {})
        display_name = name_obj.get("LocalizedString", "") if isinstance(name_obj, dict) else ""
        if not display_name:
            loc_key = f"Text_DesignData_Spell_Spell_{short_name}"
            display_name = loc.get(loc_key, to_display_name(short_name))
        # Get description from localization
        desc_key = f"Text_DataAsset_{short_name}_Desc_{short_name}Desc"
        description = loc.get(desc_key, "")
        # Extract source_type last segment
        source_type_tag = props.get("SourceType", {}).get("TagName", "")
        source_type = source_type_tag.split(".")[-1].lower() if source_type_tag else ""
        # Extract cost_type last segment
        cost_type_tag = props.get("CostType", {}).get("TagName", "")
        cost_type = cost_type_tag.split(".")[-1].lower() if cost_type_tag else ""
        # Extract casting_type last segment
        casting_type_tag = props.get("CastingType", {}).get("TagName", "")
        casting_type = casting_type_tag.split(".")[-1].lower() if casting_type_tag else ""
        spells.append({
            "id": short_name,
            "name": display_name,
            "description": description,
            "spell_tier": props.get("SpellTier", 0),
            "casting_time": props.get("CastingTime", 0.0),
            "max_count": props.get("MaxCount", 0),
            "range": props.get("Range", 0),
            "source_type": source_type,
            "cost_type": cost_type,
            "casting_type": casting_type,
        })
    return spells


def collect_shapeshifts(class_name, loc):
    """Collect shapeshifts for a class (typically Druid only)."""
    shapeshifts = []
    for path in sorted(EXTRACTED_CLASSES.glob("Id_ShapeShift_*.json")):
        data = load_json(path)
        if data is None:
            continue
        # Skip DefaultCharacter
        if "DefaultCharacter" in data.get("id", ""):
            continue
        classes = data.get("classes", [])
        if not class_matches(classes, class_name):
            continue
        ss_id = data["id"]
        short_name = extract_id_name(ss_id, "Id_ShapeShift_")
        display_name = data.get("name") or to_display_name(short_name)
        # Get description from localization (pattern: ShapeShift + name)
        desc_key = f"Text_DataAsset_ShapeShift{short_name}_Desc_ShapeShift{short_name}Desc"
        description = loc.get(desc_key, "")
        shapeshifts.append({
            "id": short_name,
            "name": display_name,
            "description": description,
            "casting_time": data.get("casting_time", 0.0),
            "capsule_radius_scale": data.get("capsule_radius_scale", 1.0),
            "capsule_height_scale": data.get("capsule_height_scale", 1.0),
        })
    return shapeshifts


def collect_spell_merge_recipes(loc):
    """Collect spell merge recipes from the SpellMergeGroup data."""
    path = RAW_V2 / "Spell" / "SpellMergeGroup" / "Id_SpellMergeGroup.json"
    data = load_json(path)
    if data is None:
        return []
    props = data[0].get("Properties", {})
    entries = props.get("SpellMergeGroupItemArray", [])
    recipes = []
    for entry in entries:
        merge_spell = entry.get("MergeSpell", {})
        merge_name_raw = merge_spell.get("PrimaryAssetName", "")
        merge_short = extract_id_name(merge_name_raw, "Id_Spell_")
        merge_display = to_display_name(merge_short)
        # Get display name from localization
        loc_key = f"Text_DesignData_Spell_Spell_{merge_short}"
        merge_display = loc.get(loc_key, merge_display)
        sources = entry.get("SourceSpells", [])
        source_names = []
        for src in sources:
            src_name_raw = src.get("PrimaryAssetName", "")
            src_short = extract_id_name(src_name_raw, "Id_Spell_")
            src_display = to_display_name(src_short)
            src_loc_key = f"Text_DesignData_Spell_Spell_{src_short}"
            src_display = loc.get(src_loc_key, src_display)
            source_names.append(src_display)
        recipes.append({
            "result": merge_display,
            "result_slug": to_slug(merge_display),
            "sources": source_names,
        })
    return recipes


def get_usable_item_count(class_name):
    """Count items usable by a class from item_classes.json."""
    data = load_json(ITEM_CLASSES_FILE)
    if data is None:
        return 0
    count = 0
    for item_name, class_list in data.items():
        if class_name in class_list or "All" in class_list:
            count += 1
    return count


def get_flavor_text(class_name, loc):
    """Get flavor text for a class from localization."""
    key = f"Text_DesignData_PlayerCharacter_PlayerCharacter_FlavorText_{class_name}"
    text = loc.get(key)
    if text:
        return text
    # Fallback: read from raw PlayerCharacter file
    path = RAW_V2 / "PlayerCharacter" / "PlayerCharacter" / f"Id_PlayerCharacter_{class_name}.json"
    data = load_json(path)
    if data is None:
        return ""
    props = data[0].get("Properties", {})
    flavor = props.get("FlavorText", {})
    return flavor.get("LocalizedString", "")


def build_class(class_name, loc):
    """Build the complete data object for a single class."""
    print(f"  Building {class_name}...")
    slug = class_name.lower()

    # Base stats
    effect_path = EXTRACTED_CLASSES / f"Id_PlayerCharacterEffect_{class_name}.json"
    effect_data = load_json(effect_path)
    if effect_data is None:
        print(f"  ERROR: Could not load base stats for {class_name}")
        return None

    base_stats = {
        "strength": effect_data.get("strength_base", 0),
        "vigor": effect_data.get("vigor_base", 0),
        "agility": effect_data.get("agility_base", 0),
        "dexterity": effect_data.get("dexterity_base", 0),
        "will": effect_data.get("will_base", 0),
        "knowledge": effect_data.get("knowledge_base", 0),
        "resourcefulness": effect_data.get("resourcefulness_base", 0),
    }

    # Derived stats
    derived_stats = compute_derived_stats(base_stats)

    # Flavor text
    flavor_text = get_flavor_text(class_name, loc)

    # Role
    role = ROLES.get(class_name, "Unknown")

    # Perks
    perks = collect_perks(class_name, loc)

    # Skills
    skills = collect_skills(class_name, loc)

    # Spells
    spells = collect_spells(class_name, loc)

    # Shapeshifts
    shapeshifts = collect_shapeshifts(class_name, loc)

    # Usable item count
    usable_item_count = get_usable_item_count(class_name)

    return {
        "slug": slug,
        "name": class_name,
        "flavor_text": flavor_text,
        "role": role,
        "base_stats": base_stats,
        "derived_stats": derived_stats,
        "perks": perks,
        "skills": skills,
        "spells": spells,
        "shapeshifts": shapeshifts,
        "usable_item_count": usable_item_count,
    }


def main():
    print("Building classes.json...")
    now = datetime.now(timezone.utc)

    # Load localization
    loc = load_localization()
    print(f"  Loaded {len(loc)} localization keys")

    # Build each class
    classes = []
    for class_name in CLASS_NAMES:
        class_data = build_class(class_name, loc)
        if class_data is not None:
            classes.append(class_data)

    # Spell merge recipes
    spell_merge_recipes = collect_spell_merge_recipes(loc)
    print(f"  Collected {len(spell_merge_recipes)} spell merge recipes")

    # Build output
    output = {
        "version": now.strftime("%Y-%m-%d"),
        "generated_at": now.isoformat(),
        "data": {
            "classes": classes,
            "spell_merge_recipes": spell_merge_recipes,
        },
    }

    # Write output
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nWrote {OUTPUT_FILE}")
    print(f"  {len(classes)} classes")
    for c in classes:
        print(
            f"    {c['name']}: {len(c['perks'])}p {len(c['skills'])}s "
            f"{len(c['spells'])}sp {len(c['shapeshifts'])}ss "
            f"items={c['usable_item_count']}"
        )


if __name__ == "__main__":
    main()
