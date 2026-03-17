"""
build_classes.py - Compile all class data into website/public/data/classes.json

Reads from:
  - extracted/classes/Id_PlayerCharacterEffect_[Class].json   (base stats)
  - raw/.../V2/PlayerCharacter/PlayerCharacter/Id_PlayerCharacter_[Class].json  (flavor text, default perks)
  - raw/.../Data/GameplayAbility/CT_*.json                    (curve tables for derived stats)
  - extracted/classes/Id_Perk_*.json                          (perks)
  - extracted/classes/Id_Skill_*.json                         (skills)
  - raw/.../V2/Spell/Spell/Id_Spell_*.json                   (spells)
  - raw/.../V2/Music/Music/Id_Music_*.json                   (bard songs)
  - extracted/classes/Id_ShapeShift_*.json                    (shapeshifts, Druid only)
  - raw/.../V2/Spell/SpellMergeGroup/Id_SpellMergeGroup.json  (spell merge recipes)
  - raw/.../Localization/Game/en/Game.json                    (localization strings)
  - website/public/data/item_classes.json                     (usable item counts)
  - raw/.../Perk/[Name]/[Name]_Desc.json                     (perk description refs)
  - raw/.../Data/DataAsset/Skill/[Name]_Desc.json            (skill description refs)
  - raw/.../Data/DataAsset/Spell/[Name]_Desc.json            (spell description refs)
  - raw/.../Data/DataAsset/Music/[Name]_Desc.json            (music description refs)
  - raw/.../Data/DataAsset/ShapeShift/ShapeShift[Name]_Desc.json  (shapeshift desc refs)
  - raw/.../V2/ActorStatus/StatusEffect/Id_ActorStatusEffect_*.json  (effect data)
  - raw/.../V2/Constant/Constant/Id_Constant_*.json          (constant values)
  - raw/.../V2/ShapeShift/ShapeShift/Id_ShapeShift_*.json    (raw shapeshift data)
  - raw/.../V2/Music/MusicEffect/Id_MusicEffect_*.json       (music damage effects)
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

PERK_DESC_DIR = RAW / "Perk"
SKILL_DESC_DIR = RAW / "Data" / "DataAsset" / "Skill"
SPELL_DESC_DIR = RAW / "Data" / "DataAsset" / "Spell"
MUSIC_DESC_DIR = RAW / "Data" / "DataAsset" / "Music"
SHAPESHIFT_DESC_DIR = RAW / "Data" / "DataAsset" / "ShapeShift"
STATUS_EFFECT_DIR = RAW_V2 / "ActorStatus" / "StatusEffect"
CONSTANT_DIR = RAW_V2 / "Constant" / "Constant"
MUSIC_EFFECT_DIR = RAW_V2 / "Music" / "MusicEffect"
SHAPESHIFT_V2_DIR = RAW_V2 / "ShapeShift" / "ShapeShift"
SHAPESHIFT_EFFECT_DIR = RAW_V2 / "ShapeShift" / "ShapeShiftEffect"
PERK_EFFECT_DIR = RAW_V2 / "Perk" / "PerkEffect"
SPELL_EFFECT_DIR = RAW_V2 / "Spell" / "SpellEffect"

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

# Properties that use /10 scale for percentage display
DIV10_PROPERTIES = {
    "ActionSpeed", "MoveSpeedMod", "PhysicalReductionMod", "ProjectileReductionMod",
    "MaxHealthMod", "RegularInteractionSpeed", "ItemArmorRatingMod",
    "PhysicalDamageMod", "MagicalDamageMod", "PhysicalHealingReceiveMod",
    "MagicalHealingReceiveMod", "SpellCastingSpeed", "CooldownReductionMod",
    "ImpactPower", "PhysicalHeadshotPower", "MagicalLightningDamageMod",
    "PhysicalReduction", "MagicalReduction",
}

# Properties that are used as-is (no division)
RAW_PROPERTIES = {
    "PhysicalDamageWeapon", "PhysicalDamageWeaponPrimary", "MoveSpeedAdd",
    "ExecMagicalDamageBase", "ExecPhysicalDamageBase", "ExecImpactPower",
    "MagicResistance", "ArmorRating", "StrengthBase", "VigorBase",
    "AgilityBase", "DexterityBase", "WillBase", "KnowledgeBase",
    "ResourcefulnessBase", "AllAttributes", "PhysicalPower",
    "MaxHealthAdd", "ExecPhysicalHealBase", "ExecMagicalDamageTrue",
}

# Fallback property name mappings: description tag name -> actual data property names
PROPERTY_NAME_FALLBACKS = {
    "PhysicalDamageWeaponPrimary": ["PhysicalDamageWeapon"],
    "PhysicalDamageWeaponSecondary": ["PhysicalDamageWeapon"],
    "MagicalDamageBase": ["ExecMagicalDamageBase"],
    "PhysicalDamageBase": ["ExecPhysicalDamageBase"],
    "PhysicalHealBase": ["ExecPhysicalHealBase"],
    "MagicalHealBase": ["ExecMagicalHealBase"],
    "MagicalDamageTrue": ["ExecMagicalDamageTrue"],
    "ArmorPenetration": ["ExecArmorPenetration"],
    "MagicalLightningDamageBase": ["ExecMagicalDamageBase"],
    "MagicalEvilDamageBase": ["ExecMagicalDamageBase"],
    "MagicalArcaneDamageBase": ["ExecMagicalDamageBase"],
    "MagicalIceDamageBase": ["ExecMagicalDamageBase"],
}


def load_json(path):
    """Load a JSON file, returning None on error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
        print(f"  WARNING: Could not load {path}: {e}")
        return None


def load_json_silent(path):
    """Load a JSON file, returning None on error without printing warnings."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
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


# ---------------------------------------------------------------------------
# Enhancement 1: Description placeholder resolution
# ---------------------------------------------------------------------------

def _load_effect_file(object_path):
    """Load an effect file from an ObjectPath reference in a _Desc.json.

    ObjectPath looks like:
      DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/ActorStatus/StatusEffect/Id_ActorStatusEffect_Foo.0
    We strip the trailing '.0' and resolve relative to the raw root.
    """
    if not object_path:
        return None
    # Strip trailing ".0" or similar
    clean = re.sub(r"\.\d+$", "", object_path)
    # Build absolute path
    path = ROOT / "raw" / (clean + ".json")
    data = load_json_silent(path)
    if data is None:
        return None
    if isinstance(data, list) and len(data) > 0:
        return data[0].get("Properties", {})
    return None


def _load_desc_file(desc_path):
    """Load a _Desc.json file and return (effects_list, constants_list, gemodifiers_list)."""
    data = load_json_silent(desc_path)
    if data is None:
        return [], [], []
    if isinstance(data, list) and len(data) > 0:
        props = data[0].get("Properties", {})
    elif isinstance(data, dict):
        props = data.get("Properties", {})
    else:
        return [], [], []

    effects = []
    for ref in props.get("DCGameplayEffectDataAssetArray", []):
        obj_path = ref.get("ObjectPath", "")
        effect_props = _load_effect_file(obj_path)
        effects.append(effect_props if effect_props else {})

    constants = []
    for ref in props.get("ConstantDataAssetArray", []):
        obj_path = ref.get("ObjectPath", "")
        const_props = _load_effect_file(obj_path)
        constants.append(const_props if const_props else {})

    gemodifiers = []
    for ref in props.get("GEModifierDataAssetArray", []):
        obj_path = ref.get("ObjectPath", "")
        gemod_props = _load_effect_file(obj_path)
        gemodifiers.append(gemod_props if gemod_props else {})

    return effects, constants, gemodifiers


def _format_number(value):
    """Format a number for display: drop trailing .0 for integers."""
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def _get_effect_value(effects, index, prop_name):
    """Get a property value from an effect at the given index."""
    if index < 0 or index >= len(effects):
        return None
    return effects[index].get(prop_name)


def _scale_property(prop_name, raw_value):
    """Apply the correct scale conversion to a property value."""
    if raw_value is None:
        return None
    if prop_name == "Duration":
        return raw_value / 1000.0
    if prop_name in DIV10_PROPERTIES:
        return raw_value / 10.0
    # Default: return as-is
    return raw_value


def resolve_description(raw_desc, desc_path):
    """Resolve description placeholders using effect/constant data from _Desc.json.

    Handles tag patterns:
      <Constant Type="Float" Format="FromZero">[N]%</>  -> constants[N].FloatValue * 100
      <Constant Type="Float">[N]%</>                    -> constants[N].FloatValue * 100
      <Constant Type="float" Format="FromOne">[N]%</>   -> abs(constants[N].FloatValue - 1) * 100
      <Duration>[N] seconds</>                          -> effects[N].Duration / 1000
      <Duration>[N]</>                                  -> effects[N].Duration / 1000
      <PropertyName>[N]% _</>                           -> effects[N].PropertyName scaled
      <PropertyName>[N] _</>                            -> effects[N].PropertyName scaled
      <PropertyName>[N1]/[N2]/[N3] _</>                 -> val1/val2/val3
      <GEMod Type="..." Format="...">[N]%</>            -> gemodifiers (best-effort)
      <Exec.PropertyName>[N]</>                         -> effects[N].ExecPropertyName
      <Perk Type="...">[N]...</>                        -> effects[N].PerkProperty (best-effort)
      <YellowColor>text</>                              -> text (just strip tags)
      <PropertyName>_</>                                -> display name of property
      <PropertyName>_ text</>                           -> display name + text
    """
    if not raw_desc:
        return raw_desc

    effects, constants, gemodifiers = _load_desc_file(desc_path)

    text = raw_desc

    # 1. Handle <Constant Type="Float" Format="FromZero">[N]%</> and variants
    def replace_constant_from_zero(m):
        idx = int(m.group("idx"))
        suffix = m.group("suffix")
        if idx < len(constants) and constants[idx]:
            val = constants[idx].get("FloatValue", 0)
            formatted = _format_number(abs(val) * 100)
            return formatted + suffix
        return m.group(0)

    text = re.sub(
        r'<Constant\s+Type="[Ff]loat"\s+Format="FromZero">\[(?P<idx>\d+)\](?P<suffix>[^<]*)</>',
        replace_constant_from_zero, text
    )

    # 1b. Handle <Constant Type="float" Format="FromOne">[N]%</> (relative to 1.0)
    def replace_constant_from_one(m):
        idx = int(m.group("idx"))
        suffix = m.group("suffix")
        if idx < len(constants) and constants[idx]:
            val = constants[idx].get("FloatValue", 0)
            formatted = _format_number(abs(val - 1.0) * 100)
            return formatted + suffix
        return m.group(0)

    text = re.sub(
        r'<Constant\s+Type="[Ff]loat"\s+Format="FromOne">\[(?P<idx>\d+)\](?P<suffix>[^<]*)</>',
        replace_constant_from_one, text
    )

    # 1c. Handle <Constant Type="Float">[N]%</> (no format specified, assume raw * 100)
    def replace_constant_plain(m):
        idx = int(m.group("idx"))
        suffix = m.group("suffix")
        if idx < len(constants) and constants[idx]:
            val = constants[idx].get("FloatValue", 0)
            formatted = _format_number(abs(val) * 100)
            return formatted + suffix
        return m.group(0)

    text = re.sub(
        r'<Constant\s+Type="[Ff]loat">\[(?P<idx>\d+)\](?P<suffix>[^<]*)</>',
        replace_constant_plain, text
    )

    # 2. Handle <Duration>[N] seconds</> and <Duration>[N]</>
    def replace_duration(m):
        idx = int(m.group("idx"))
        suffix = m.group("suffix")
        val = _get_effect_value(effects, idx, "Duration")
        if val is not None:
            seconds = val / 1000.0
            return _format_number(seconds) + suffix
        return m.group(0)

    text = re.sub(
        r'<Duration>\[(?P<idx>\d+)\](?P<suffix>[^<]*)</>',
        replace_duration, text
    )

    # 3. Handle <GEMod Type="Multiply" Format="FromOne">[N]%</> and similar
    # GEMod tags are complex; best-effort: strip tags but keep content
    def replace_gemod(m):
        fmt = m.group("format") or ""
        content = m.group("content")
        # Try to resolve index references in the content
        return content

    text = re.sub(
        r'<GEMod\s+[^>]*?(?:Format="(?P<format>[^"]*)")?\s*[^>]*>\s*(?P<content>[^<]*)</>',
        replace_gemod, text
    )

    # 4. Handle <Exec.PropertyName>[N] .../> patterns
    def replace_exec_prop(m):
        prop_name = m.group("prop")
        idx = int(m.group("idx"))
        suffix = m.group("suffix")
        # Map Exec.X to ExecX in effect properties
        exec_key = "Exec" + prop_name
        # Also try without the Exec prefix
        val = _get_effect_value(effects, idx, exec_key)
        if val is None:
            val = _get_effect_value(effects, idx, prop_name)
        if val is not None:
            # PrimitiveCalcMultiply and PrimitiveCalcAdd need /100 scaling
            if "PrimitiveCalcMultiply" in prop_name and "%" in suffix:
                val = val / 100.0
            formatted = _format_number(val)
            has_label = "_" in suffix
            clean_suffix = suffix.replace(" _", "").replace("_", "").strip()
            if has_label:
                prop_display = to_display_name(prop_name)
                if clean_suffix:
                    return formatted + clean_suffix + " " + prop_display
                return formatted + " " + prop_display
            if clean_suffix:
                return formatted + clean_suffix
            return formatted
        return m.group(0)

    text = re.sub(
        r'<Exec\.(?P<prop>\w+)>\[(?P<idx>\d+)\](?P<suffix>[^<]*)</>',
        replace_exec_prop, text
    )

    # 5. Handle <PropertyName>[N1]/[N2]/[N3] _</> (multi-index, e.g., bad/good/perfect)
    def replace_multi_index(m):
        prop_name = m.group("prop")
        indices_str = m.group("indices")
        suffix = m.group("suffix")
        indices = [int(x) for x in re.findall(r'\[(\d+)\]', indices_str)]
        values = []
        for idx in indices:
            val = _get_effect_value(effects, idx, prop_name)
            if val is not None:
                scaled = _scale_property(prop_name, val)
                values.append(_format_number(scaled))
            else:
                values.append(f"[{idx}]")
        result = "/".join(values)
        # Check if _ is present as a label placeholder
        has_label = "_" in suffix
        # Clean suffix: replace leading " _" marker
        clean_suffix = suffix.replace(" _", "").replace("_", "").strip()
        if has_label:
            prop_display = to_display_name(prop_name)
            if clean_suffix:
                return result + clean_suffix + " " + prop_display
            return result + " " + prop_display
        if clean_suffix:
            return result + " " + clean_suffix
        return result

    text = re.sub(
        r'<(?P<prop>[A-Z]\w+)>(?P<indices>(?:\[\d+\]/)+\[\d+\])(?P<suffix>[^<]*)</>',
        replace_multi_index, text
    )

    # 6. Handle <PropertyName>[N]% _</> and <PropertyName>[N] _</>
    #    Also handles <PropertyName> [N]% _</> (space after tag opening)
    def replace_property_with_index(m):
        prop_name = m.group("prop")
        idx = int(m.group("idx"))
        suffix = m.group("suffix")
        val = _get_effect_value(effects, idx, prop_name)
        # Try fallback property name mappings
        if val is None:
            fallbacks = PROPERTY_NAME_FALLBACKS.get(prop_name, [])
            for fb in fallbacks:
                val = _get_effect_value(effects, idx, fb)
                if val is not None:
                    break
        if val is not None:
            scaled = _scale_property(prop_name, val)
            formatted = _format_number(scaled)
            # Check if _ is present as a label placeholder for the property name
            has_label = "_" in suffix
            # Clean suffix: remove the _ marker
            clean_suffix = suffix.replace(" _", "").replace("_", "").strip()
            if has_label:
                # Include the property display name
                prop_display = to_display_name(prop_name)
                if clean_suffix:
                    return formatted + clean_suffix + " " + prop_display
                return formatted + " " + prop_display
            if clean_suffix:
                return formatted + clean_suffix
            return formatted
        return m.group(0)

    text = re.sub(
        r'<(?P<prop>[A-Z]\w+)>\s*\[(?P<idx>\d+)\](?P<suffix>[^<]*)</>',
        replace_property_with_index, text
    )

    # 7. Handle <MovementMod Type="..." Format="...">[N]%</> - best effort strip
    text = re.sub(
        r'<MovementMod\s+[^>]*>\[(\d+)\]([^<]*)</>',
        lambda m: m.group(0),  # Keep as-is since we can't resolve movement mods
        text
    )

    # 8. Handle <Perk Type="...">[N]...</>  - best effort strip
    text = re.sub(
        r'<Perk\s+[^>]*>\[(\d+)\]([^<]*)</>',
        lambda m: m.group(0),  # Keep as-is since we can't resolve perk refs
        text
    )

    # 9. Handle <YellowColor>text</> - just keep the inner text
    text = re.sub(r'<YellowColor>([^<]*)</>', r'\1', text)

    # 10. Handle remaining <PropertyName>_</> (label-only tags, no value)
    # These are display labels like <MagicalReduction>_</> meaning "Magical Reduction"
    def replace_label_tag(m):
        prop_name = m.group("prop")
        inner = m.group("inner").strip()
        if inner == "_" or inner == "":
            # Convert property name to display name
            display = to_display_name(prop_name)
            # Lowercase it since it appears mid-sentence
            return display.lower()
        # If there's content besides _, keep it
        clean = inner.replace("_", "").strip()
        if clean:
            return clean
        return to_display_name(prop_name).lower()

    text = re.sub(
        r'<(?P<prop>[A-Z]\w+)>(?P<inner>[^<\[]*)</>' ,
        replace_label_tag, text
    )

    # 11. Handle <Exec.PropertyName>_</> (label-only exec tags)
    text = re.sub(
        r'<Exec\.(\w+)>([^<\[]*)</>',
        lambda m: to_display_name(m.group(1)).lower() if m.group(2).strip() in ("_", "") else m.group(2).replace("_", "").strip(),
        text
    )

    # 12. Clean up remaining artifacts
    # Remove any leftover </> tags
    text = re.sub(r'</>', '', text)
    # Remove any remaining <...> tags that weren't matched
    text = re.sub(r'<[^>]+>', '', text)
    # Clean up double spaces
    text = re.sub(r'  +', ' ', text)
    # Clean up spaces before punctuation
    text = re.sub(r' +([,.])', r'\1', text)
    # Strip
    text = text.strip()

    return text


def _find_desc_path_perk(short_name):
    """Find the _Desc.json file for a perk."""
    return PERK_DESC_DIR / short_name / f"{short_name}_Desc.json"


def _find_desc_path_skill(short_name):
    """Find the _Desc.json file for a skill."""
    return SKILL_DESC_DIR / f"{short_name}_Desc.json"


def _find_desc_path_spell(short_name):
    """Find the _Desc.json file for a spell."""
    return SPELL_DESC_DIR / f"{short_name}_Desc.json"


def _find_desc_path_music(short_name):
    """Find the _Desc.json file for a music/song."""
    return MUSIC_DESC_DIR / f"{short_name}_Desc.json"


def _find_desc_path_shapeshift(short_name):
    """Find the _Desc.json file for a shapeshift."""
    return SHAPESHIFT_DESC_DIR / f"ShapeShift{short_name}_Desc.json"


def try_resolve_description(raw_desc, desc_path):
    """Try to resolve description placeholders. Fall back to simple tag stripping on failure."""
    if not raw_desc:
        return raw_desc
    try:
        if desc_path.exists():
            resolved = resolve_description(raw_desc, desc_path)
            return resolved
    except Exception as e:
        print(f"  WARNING: Description resolution failed for {desc_path}: {e}")
    # Fallback: simple tag stripping
    return strip_description_tags(raw_desc)


def strip_description_tags(desc):
    """Simple fallback: strip XML-like tags from description text."""
    if not desc:
        return desc
    text = re.sub(r'<YellowColor>([^<]*)</>', r'\1', desc)
    text = re.sub(r'</>', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'  +', ' ', text)
    return text.strip()


# ---------------------------------------------------------------------------
# Enhancement 2: Rich ShapeShift data
# ---------------------------------------------------------------------------

def _read_shapeshift_stat_modifiers(short_name):
    """Read stat modifiers from the ShapeShift StatusEffect file."""
    effect_path = STATUS_EFFECT_DIR / f"Id_ActorStatusEffect_ShapeShift{short_name}.json"
    data = load_json_silent(effect_path)
    if data is None:
        return {}

    props = data[0].get("Properties", {}) if isinstance(data, list) and data else {}

    modifiers = {}
    # Map raw properties to clean output keys with appropriate scaling
    mod_mappings = {
        "MaxHealthMod": "max_health_pct",
        "PhysicalReductionMod": "physical_reduction_pct",
        "ProjectileReductionMod": "projectile_reduction_pct",
        "MoveSpeedMod": "move_speed_pct",
        "ActionSpeed": "action_speed_pct",
        "MoveSpeedAdd": "move_speed_add",
        "PhysicalHealingReceiveMod": "physical_healing_receive_pct",
        "MagicalHealingReceiveMod": "magical_healing_receive_pct",
        "PhysicalReduction": "physical_reduction_flat_pct",
        "MagicalReduction": "magical_reduction_flat_pct",
    }

    for raw_key, out_key in mod_mappings.items():
        val = props.get(raw_key)
        if val is not None:
            if raw_key in DIV10_PROPERTIES:
                modifiers[out_key] = val / 10.0
            elif raw_key in RAW_PROPERTIES:
                modifiers[out_key] = val
            else:
                modifiers[out_key] = val

    return modifiers


def _read_shapeshift_form_skill(short_name, loc):
    """Read the form skill name and description from the raw ShapeShift data."""
    ss_path = SHAPESHIFT_V2_DIR / f"Id_ShapeShift_{short_name}.json"
    data = load_json_silent(ss_path)
    if data is None:
        return None, ""

    props = data[0].get("Properties", {}) if isinstance(data, list) and data else {}
    skills = props.get("Skills", [])

    # The form skill is typically the second entry (after ShapeShiftMemory1)
    form_skill_id = None
    for skill_ref in skills:
        asset_path = skill_ref.get("AssetPathName", "")
        # Extract skill ID from path
        parts = asset_path.split(".")
        if parts:
            skill_id = parts[-1]
            skill_short = extract_id_name(skill_id, "Id_Skill_")
            if skill_short != "ShapeShiftMemory1" and skill_short != "ShapeShiftMemory2":
                form_skill_id = skill_short
                break

    if not form_skill_id:
        return None, ""

    # Get display name from localization
    loc_key = f"Text_DesignData_Skill_Skill_{form_skill_id}"
    display_name = loc.get(loc_key, to_display_name(form_skill_id))

    # Get description from localization - try multiple key patterns
    desc_key = f"Text_DataAsset_{form_skill_id}_Desc_{form_skill_id}Desc"
    raw_desc = loc.get(desc_key, "")
    if not raw_desc:
        # Try with "Attack" suffix variant (e.g., WildFuryAttack)
        desc_key_alt = f"Text_DataAsset_{form_skill_id}Attack_Desc_{form_skill_id}Desc"
        raw_desc = loc.get(desc_key_alt, "")

    # Try to resolve the description
    desc_path = SKILL_DESC_DIR / f"{form_skill_id}_Desc.json"
    description = try_resolve_description(raw_desc, desc_path)

    return display_name, description


# ---------------------------------------------------------------------------
# Enhancement 3: Bard song performance tiers
# ---------------------------------------------------------------------------

def _read_song_tier_effects(short_name):
    """Read tier-specific effects for a Bard song.

    For buff songs: look for ActorStatusEffect_{short_name}_{Bad|Good|Perfect}
    For damage songs: look for MusicEffect_{short_name}_{Bad|Good|Perfect}
    """
    tier_effects = {}
    tiers = ["Bad", "Good", "Perfect"]

    for tier in tiers:
        tier_data = {}

        # Try ActorStatusEffect (buff songs)
        se_path = STATUS_EFFECT_DIR / f"Id_ActorStatusEffect_{short_name}_{tier}.json"
        se_data = load_json_silent(se_path)
        if se_data is not None:
            props = se_data[0].get("Properties", {}) if isinstance(se_data, list) and se_data else {}
            duration = props.get("Duration")
            if duration is not None:
                tier_data["duration_ms"] = duration

            # Capture all gameplay properties (skip metadata keys)
            skip_keys = {"EffectClass", "EventTag", "TargetType", "Duration",
                         "AssetTags", "V1Data"}
            for key, val in props.items():
                if key not in skip_keys and not isinstance(val, (dict, list)):
                    tier_data[key] = val

        # Try MusicEffect (damage songs)
        me_path = MUSIC_EFFECT_DIR / f"Id_MusicEffect_{short_name}_{tier}.json"
        me_data = load_json_silent(me_path)
        if me_data is not None:
            props = me_data[0].get("Properties", {}) if isinstance(me_data, list) and me_data else {}
            skip_keys = {"EffectClass", "EventTag", "TargetType", "V1Data"}
            for key, val in props.items():
                if key not in skip_keys and not isinstance(val, (dict, list)):
                    tier_data[key] = val

        if tier_data:
            tier_effects[tier.lower()] = tier_data

    return tier_effects if tier_effects else None


# ---------------------------------------------------------------------------
# Existing collection functions (enhanced with description resolution)
# ---------------------------------------------------------------------------

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
        raw_description = loc.get(desc_key, "")
        # Resolve description placeholders
        desc_path = _find_desc_path_perk(short_name)
        description = try_resolve_description(raw_description, desc_path)
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
        raw_description = loc.get(desc_key, "")
        # Resolve description placeholders
        desc_path = _find_desc_path_skill(short_name)
        description = try_resolve_description(raw_description, desc_path)
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
        raw_description = loc.get(desc_key, "")
        # Resolve description placeholders
        desc_path = _find_desc_path_spell(short_name)
        description = try_resolve_description(raw_description, desc_path)
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


def collect_songs(class_name, loc):
    """Collect all Bard songs for a given class from raw music files."""
    songs = []
    music_dir = RAW_V2 / "Music" / "Music"
    if not music_dir.exists():
        return songs
    for path in sorted(music_dir.glob("Id_Music_*.json")):
        data = load_json(path)
        if data is None:
            continue
        props = data[0].get("Properties", {})
        # Check class membership via PrimaryAssetName
        classes = props.get("Classes", [])
        if not class_matches(classes, class_name):
            continue
        music_id = data[0].get("Name", "")
        short_name = extract_id_name(music_id, "Id_Music_")
        # Get display name from localization or Properties.Name
        name_obj = props.get("Name", {})
        display_name = name_obj.get("LocalizedString", "") if isinstance(name_obj, dict) else ""
        if not display_name:
            loc_key = f"Text_DesignData_Music_Music_{short_name}"
            display_name = loc.get(loc_key, to_display_name(short_name))
        # Get description from localization
        desc_key = f"Text_DataAsset_{short_name}_Desc_{short_name}Desc"
        raw_description = loc.get(desc_key, "")
        # Resolve description placeholders
        desc_path = _find_desc_path_music(short_name)
        description = try_resolve_description(raw_description, desc_path)
        # Extract source_type last segment
        source_type_tag = props.get("SourceType", {}).get("TagName", "")
        source_type = source_type_tag.split(".")[-1].lower() if source_type_tag else ""
        # Extract casting_type from PlayType last segment
        play_type_tag = props.get("PlayType", {}).get("TagName", "")
        casting_type = play_type_tag.split(".")[-1].lower() if play_type_tag else ""

        song_entry = {
            "id": short_name,
            "name": display_name,
            "description": description,
            "spell_tier": props.get("MusicTier", 0),
            "casting_time": None,
            "max_count": None,
            "range": None,
            "source_type": source_type,
            "cost_type": "music",
            "casting_type": casting_type,
        }

        # Enhancement 3: Add performance tier ranges
        bad_range = props.get("BadRange")
        good_range = props.get("GoodRange")
        perfect_range = props.get("PerfectRange")
        if bad_range is not None:
            song_entry["bad_range"] = bad_range
        if good_range is not None:
            song_entry["good_range"] = good_range
        if perfect_range is not None:
            song_entry["perfect_range"] = perfect_range

        # Enhancement 3: Add tier-specific effects
        tier_effects = _read_song_tier_effects(short_name)
        if tier_effects:
            song_entry["tier_effects"] = tier_effects

        songs.append(song_entry)
    return songs


def collect_shapeshifts(class_name, loc):
    """Collect shapeshifts for a class (typically Druid only)."""
    shapeshifts = []
    for path in sorted(EXTRACTED_CLASSES.glob("Id_ShapeShift_*.json")):
        data = load_json(path)
        if data is None:
            continue
        # Skip DefaultCharacter and BloodPact (Warlock form, not Druid)
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
        raw_description = loc.get(desc_key, "")
        # Resolve description placeholders
        desc_path = _find_desc_path_shapeshift(short_name)
        description = try_resolve_description(raw_description, desc_path)

        ss_entry = {
            "id": short_name,
            "name": display_name,
            "description": description,
            "casting_time": data.get("casting_time", 0.0),
            "capsule_radius_scale": data.get("capsule_radius_scale", 1.0),
            "capsule_height_scale": data.get("capsule_height_scale", 1.0),
        }

        # Enhancement 2: Add stat modifiers from StatusEffect file
        stat_mods = _read_shapeshift_stat_modifiers(short_name)
        if stat_mods:
            ss_entry["stat_modifiers"] = stat_mods

        # Enhancement 2: Add form skill
        form_skill_name, form_skill_desc = _read_shapeshift_form_skill(short_name, loc)
        if form_skill_name:
            ss_entry["form_skill"] = form_skill_name
            ss_entry["form_skill_description"] = form_skill_desc

        shapeshifts.append(ss_entry)
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

    # Songs (Bard music) - merge into spells list
    songs = collect_songs(class_name, loc)
    if songs:
        spells.extend(songs)

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
