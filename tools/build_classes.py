"""
build_classes.py - Compile all class data into website/public/data/classes.json

GAME UPDATE WORKFLOW:
  1. Re-export from FModel (see docs/pipeline/game-update-workflow.md)
  2. Run: py -3 -m pipeline.extract_all --force
  3. Run: py -3 tools/build_classes.py
  4. Check for new missing icons or descriptions
  5. If GEModifier values changed, re-scan .uexp files (see GEMODIFIER_VALUES section)

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
  - raw/.../ActorStatus/Buff/Perk/[Name]/GE_*.json           (perk activation conditions)
  - raw/.../V2/Spell/SpellEffect/Id_SpellEffect_*.json       (spell scaling formulas)
  - raw/.../V2/Skill/SkillEffect/Id_SkillEffect_*.json       (skill scaling formulas)
"""

# ═══════════════════════════════════════════════════════════════════════
# SECTION: Imports & Constants
# Standard library imports and directory path constants.
# ═══════════════════════════════════════════════════════════════════════

import json
import re
import shutil
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

ICONS_SRC = Path(r"C:\Users\pawel\Desktop\Projects\Output\Exports\DungeonCrawler\Content\DungeonCrawler\UI\Resources")
ICONS_DST = ROOT / "website" / "public" / "icons"

MOVEMENT_MODIFIER_DIR = RAW_V2 / "MovementModifier" / "MovementModifier"
MELEE_ATTACK_DIR = RAW_V2 / "MeleeAttack" / "MeleeAttack"

# ═══════════════════════════════════════════════════════════════════════
# SECTION: Hardcoded Values
# These values couldn't be extracted from JSON and require manual updates.
# See docs/pipeline/game-update-workflow.md for re-extraction instructions.
# ═══════════════════════════════════════════════════════════════════════

# GEModifier float values extracted from binary .uexp files.
# The JSON exports have corrupted float fields; these are the correct values.
GEMODIFIER_VALUES = {
    "Id_GEModifier_HeavySwing": -0.1,
    "Id_GEModifier_PotionChugger_Duration": 0.5,
    "Id_GEModifier_PotionChugger_HealingPotion": 1.2,
    "Id_GEModifier_PotionChugger_MagicalProtection": 1.2,
    "Id_GEModifier_PotionChugger_ProtectionPotion": 1.2,
    "Id_GEModifier_TreacherousLungs_Buff": 1.5,
    "Id_GEModifier_TreacherousLungs_Debuff": 1.5,
    "Id_GEModifier_HideMastery": 1.5,
    "Id_GEModifier_HideMastery_CooldownReduction": 0.7,
    "Id_GEModifier_LightningMastery": 1.0,
    "Id_GEModifier_ManaFold": 0.75,
    "Id_GEModifier_ShapeShiftMastery": 0.75,
    "Id_GEModifier_ShapeShiftMastery_ShapeShift": 0.5,
    "Id_GEModifier_SpellSculpting": 1.25,
    "Id_GEModifier_TimeDistortion": 2.0,
    "Id_GEModifier_TortureMastery": 2.0,
    "Id_GEModifier_CampingMastery": 2.0,
    "Id_GEModifier_BrewMaster": 1.5,
}

# Values stored in compiled Blueprints, not accessible from JSON exports.
# These are verified against community wiki data.
BLUEPRINT_HARDCODED = {
    "ExecExecutionHealthRatioThreshold": 20,  # FinishingBlow: 20% health threshold
}

# Localization key overrides for abilities with typos in Game.json keys
DESCRIPTION_KEY_OVERRIDES = {
    "UnchainedHarmony": "Text_DataAsset_UnchaninedHarmony_Desc_UnchaninedHarmonyDesc",
    "FortifiedGround": "Text_DataAsset_FortifiedGround_Desc_FortifiedGroudDesc",
    "TrapMastery": "Text_DataAsset_TrapMasteryt_Desc_TrapMasteryDesc",
    "CurseofPain": "Text_DataAsset_CurseofPain_Desc_CurseofPain",
    "FlamefrostSpear": "Text_DataAsset_FlameFrostSpear_Desc_FlameFrostSpearDesc",
}

# Hardcoded descriptions for abilities with no localization entry
DESCRIPTION_HARDCODES = {
    "SorceryCombat": "Suppresses the caster's sorcery abilities.",
    "SorceryCombat1": "Suppresses the caster's sorcery abilities.",
    "SorceryCombat2": "Suppresses the caster's sorcery abilities.",
    "SuppressSorcery": "Suppresses the caster's sorcery abilities.",
}

# Icon filename overrides for abilities whose icons don't follow standard naming
ICON_OVERRIDES = {
    ("skills", "MusicMemory1"): "Icon_Skill_MusicMemory.png",
    ("skills", "MusicMemory2"): "Icon_Skill_MusicMemory.png",
    ("skills", "SpellMemory1"): "Icon_Skill_SpellMemory.png",
    ("skills", "SpellMemory2"): "Icon_Skill_SpellMemory.png",
    ("skills", "ShapeShiftMemory1"): "Icon_Skill_ShapeShiftMemory.png",
    ("skills", "ShapeShiftMemory2"): "Icon_Skill_ShapeShiftMemory.png",
    ("skills", "Sorcery1"): "Icon_Skill_SpellMemory.png",
    ("skills", "Sorcery2"): "Icon_Skill_SpellMemory.png",
    ("perks", "ComboAttack"): "Icon_Perk_ComboAttack.png",
    ("spells", "SummonEarthElemental"): "Icon_Spell_SummonEarthElemental.png",
    ("spells", "SorceryCombat"): "Icon_Spell_SorceryCombat.png",
    ("spells", "SorceryCombat1"): "Icon_Spell_SorceryCombat.png",
    ("spells", "SorceryCombat2"): "Icon_Spell_SorceryCombat.png",
    ("perks", "HideMastery"): "Icon_Perk_HideMastery.png",
    ("spells", "SummonLavaElemental"): "Icon_Spell_LavaElemental.png",
}

PERK_GE_DIR = RAW / "ActorStatus" / "Buff" / "Perk"

PERK_DESC_DIR = RAW / "Perk"
SKILL_DESC_DIR = RAW / "Data" / "DataAsset" / "Skill"
SPELL_DESC_DIR = RAW / "Data" / "DataAsset" / "Spell"
MUSIC_DESC_DIR = RAW / "Data" / "DataAsset" / "Music"
MUSIC_PLAY_DIR = RAW / "Data" / "DataAsset" / "Music"
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
    "MagicalDivineDamageMod", "MagicalFireDamageMod", "MagicalDarkDamageMod",
    "MoveSpeedArmorPenaltyMod", "AllAttributesMod", "MaxSpellCountMod",
    "HeadshotReductionMod", "MovespeedMod", "knowledgeMod", "KnowledgeMod",
    "MagicalReductionMod", "PhysicalReductionMod",
    "StrengthMod", "VigorMod", "AgilityMod", "DexterityMod",
    "WillMod", "KnowledgeMod", "ResourcefulnessMod",
    # Health ratio properties (raw 400 = 40%, raw -100 = -10%)
    "ExecAddHealthByMaxHealthRatio", "ExecAddHealthbyMaxHealthRatio",
    "ExecHealthCostByMaxHealthRatio",
    # Headshot/backstab/penetration properties (raw 500 = 50%, etc.)
    "PhysicalHeadshotPenetration", "PhysicalBackstabPower",
    "ArmorPenetration",
    # Damage modifier properties (raw 200 = 20%)
    "UndeadDamageMod", "MagicalHealMod",
    # Attribute scaling ratio (raw 250 = 25%)
    "ExecAttributeBonusRatio",
}

# Properties that are used as-is (no division)
RAW_PROPERTIES = {
    "PhysicalDamageWeapon", "PhysicalDamageWeaponPrimary", "MoveSpeedAdd",
    "ExecMagicalDamageBase", "ExecPhysicalDamageBase", "ExecImpactPower",
    "MagicResistance", "ArmorRating", "StrengthBase", "VigorBase",
    "AgilityBase", "DexterityBase", "WillBase", "KnowledgeBase",
    "ResourcefulnessBase", "AllAttributes", "PhysicalPower",
    "MaxHealthAdd", "ExecPhysicalHealBase", "ExecMagicalDamageTrue",
    "ExecAddRecoverableHealth",
    "MagicalDamageWeaponPrimary", "MaxTotalShield",
    "ExecExecutionHealthRatioThreshold", "ExecPhysicalDamageTrue",
    "ExecRecoveryHealBase", "ExecMagicalHealBase",
    "PhysicalDamageWeaponSecondary",
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
    "AddHealthbyMaxHealthRatio": ["ExecAddHealthByMaxHealthRatio", "ExecAddHealthbyMaxHealthRatio"],
    "AddHealthByMaxHealthRatio": ["ExecAddHealthByMaxHealthRatio", "ExecAddHealthbyMaxHealthRatio"],
    "AddRecoverableHealth": ["ExecAddRecoverableHealth"],
    "HealthCostByMaxHealthRatio": ["ExecHealthCostByMaxHealthRatio"],
    "MagicalSpiritDamageBase": ["ExecMagicalDamageBase"],
    "MagicalDivineDamageBase": ["ExecMagicalDamageBase"],
    "MagicalFireDamageBase": ["ExecMagicalDamageBase"],
    "MagicalEarthDamageBase": ["ExecMagicalDamageBase"],
    "MagicalDarkDamageBase": ["ExecMagicalDamageBase"],
    "RecoveryHealBase": ["ExecRecoveryHealBase"],
    "ExecutionHealthRatioThreshold": ["ExecExecutionHealthRatioThreshold"],
    "PhysicalDamageTrue": ["ExecPhysicalDamageTrue", "ExecMagicalDamageTrue"],
    "ImpactPower": ["ExecImpactPower"],
    "Vigorbase": ["VigorBase"],  # case-sensitivity fix
    "knowledgeMod": ["KnowledgeMod"],  # case-sensitivity fix
    "MovespeedMod": ["MoveSpeedMod"],  # case-sensitivity fix
    "MoveSpeedArmorPenaltyMod": ["MoveSpeedArmorPenaltyMod"],
    "PhysicalDamageWeaponSecondary": ["PhysicalDamageWeapon", "PhysicalDamageWeaponPrimary"],
    "MagicalDamageWeaponPrimary": ["MagicalDamageWeapon"],
}

# Tag property name -> human-readable display name
PROPERTY_DISPLAY_NAMES = {
    "MoveSpeedMod": "Move Speed",
    "MoveSpeedAdd": "Move Speed",
    "MoveSpeedArmorPenaltyMod": "Move Speed Penalty",
    "ActionSpeed": "Action Speed",
    "PhysicalDamageWeaponPrimary": "Physical Damage",
    "PhysicalDamageWeaponSecondary": "Physical Damage",
    "PhysicalDamageWeapon": "Physical Damage",
    "ItemArmorRatingMod": "Armor Rating",
    "ArmorRating": "Armor Rating",
    "MagicResistance": "Magic Resistance",
    "MaxHealthMod": "Max Health",
    "MaxHealthAdd": "Max Health",
    "RegularInteractionSpeed": "Interaction Speed",
    "PhysicalReduction": "Physical Damage Reduction",
    "PhysicalReductionMod": "Physical Damage Reduction",
    "ProjectileReductionMod": "Projectile Damage Reduction",
    "MagicalReduction": "Magical Damage Reduction",
    "MagicalReductionMod": "Magical Damage Reduction",
    "SpellCastingSpeed": "Spell Casting Speed",
    "KnowledgeMod": "Knowledge",
    "knowledgeMod": "Knowledge",
    "StrengthBase": "Strength",
    "VigorBase": "Vigor",
    "Vigorbase": "Vigor",
    "WillBase": "Will",
    "KnowledgeBase": "Knowledge",
    "AgilityBase": "Agility",
    "DexterityBase": "Dexterity",
    "ResourcefulnessBase": "Resourcefulness",
    "AllAttributes": "All Attributes",
    "AllAttributesMod": "All Attributes",
    "PhysicalHealingReceiveMod": "Physical Healing",
    "MagicalHealingReceiveMod": "Magical Healing",
    "PhysicalPower": "Physical Power",
    "MagicalPower": "Magical Power",
    "PhysicalDamageBase": "Physical Damage",
    "PhysicalDamageMod": "Physical Damage",
    "MagicalDamageBase": "Magical Damage",
    "MagicalDamageMod": "Magical Damage",
    "ExecMagicalDamageBase": "Magical Damage",
    "ExecPhysicalDamageBase": "Physical Damage",
    "ImpactPowerMod": "Impact Power",
    "ImpactPower": "Impact Power",
    "HeadshotPowerMod": "Headshot Power",
    "HeadshotReductionMod": "Headshot Damage Reduction",
    "ArmorPenetration": "Armor Penetration",
    "ExecArmorPenetration": "Armor Penetration",
    "CooldownReductionMod": "Cooldown",
    "MagicalDivineDamageMod": "Magical Divine Damage",
    "MagicalFireDamageMod": "Magical Fire Damage",
    "MagicalLightningDamageMod": "Magical Lightning Damage",
    "MagicalDarkDamageMod": "Magical Dark Damage",
    "MagicalDivineDamageBase": "magical divine damage",
    "MagicalFireDamageBase": "magical fire damage",
    "MagicalLightningDamageBase": "magical lightning damage",
    "MagicalDarkDamageBase": "magical dark damage",
    "MagicalEvilDamageBase": "magical evil damage",
    "MagicalSpiritDamageBase": "magical spirit damage",
    "MagicalArcaneDamageBase": "magical arcane damage",
    "MagicalIceDamageBase": "magical ice damage",
    "MagicalEarthDamageBase": "magical earth damage",
    "MovespeedMod": "Move Speed",
    "MoveSpeedArmorPenaltyMod": "Move Speed Penalty",
    "MaxSpellCountMod": "Spell Count",
    "MagicalDamageWeaponPrimary": "Magical Damage",
    "MaxTotalShield": "Shield",
    "AddHealthByMaxHealthRatio": "Max Health",
    "AddHealthbyMaxHealthRatio": "Max Health",
    "AddRecoverableHealth": "Recoverable Health",
    "HealthCostByMaxHealthRatio": "Max Health",
    "ExecutionHealthRatioThreshold": "Health Threshold",
    "PhysicalDamageTrue": "true physical damage",
    "RecoveryHealBase": "Recovery Heal",
    "PhysicalHeadshotPenetration": "Headshot Penetration",
    "PhysicalBackstabPower": "Backstab Damage",
    "UndeadDamageMod": "Undead Damage",
    "MagicalHealMod": "Magical Healing",
    "ExecAttributeBonusRatio": "Attribute Scaling",
}


# ═══════════════════════════════════════════════════════════════════════
# SECTION: Core Utilities
# JSON loading, localization, slugification, and display name conversion.
# ═══════════════════════════════════════════════════════════════════════


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


# ═══════════════════════════════════════════════════════════════════════
# SECTION: Curve Table Interpolation
# Loads CT_*.json curve tables and linearly interpolates derived stats
# (health, move speed, action speed, etc.) from base attribute values.
# ═══════════════════════════════════════════════════════════════════════


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
    ct_phys_dmg_mod = load_curve_table("CT_PhysicalPower.json", "PhysicalDamageMod")
    ct_mag_dmg_mod = load_curve_table("CT_MagicalPower.json", "MagicalDamageMod")
    ct_mag_interact = load_curve_table("CT_Will.json", "MagicalInteractionSpeed")
    ct_spell_recovery = load_curve_table("CT_RecoveryMod.json", "MemoryRecoveryMod")
    ct_persuasiveness = load_curve_table("CT_Resourcefulness.json", "Persuasiveness")
    ct_cooldown = load_curve_table("CT_Resourcefulness.json", "CooldownReduction")
    ct_armor_reduction = load_curve_table("CT_ArmorRating.json", "PhysicalReduction")

    health = lerp_curve(ct_health, vigor)
    move_speed_mod = lerp_curve(ct_move_speed, agility)
    move_speed = 300 + move_speed_mod

    # Physical Damage Reduction from armor rating (base = 0 armor for naked character)
    # At 0 armor rating the curve gives PhysicalReduction directly
    phys_dmg_reduction_raw = lerp_curve(ct_armor_reduction, 0)
    phys_dmg_reduction_pct = round(phys_dmg_reduction_raw * 100, 1)

    # Magic Power: Will -> MagicalPower via CT_Will.json (1:1 linear curve)
    ct_magic_power = load_curve_table("CT_Will.json", "MagicalPower")

    return {
        "health": round(health, 1),
        "move_speed": round(move_speed, 1),
        "move_speed_pct": round(move_speed_mod / 3, 1),  # base is 300, so pct = mod/3
        "action_speed_pct": round(lerp_curve(ct_action_speed, agility) * 100, 1),
        "spell_casting_speed_pct": round(lerp_curve(ct_spell_speed, knowledge) * 100, 1),
        "memory_capacity": round(lerp_curve(ct_mem_cap, knowledge)),
        "magic_resistance_pct": round(lerp_curve(ct_magic_res, will), 1),
        "physical_power": round(lerp_curve(ct_phys_power, strength), 1),
        "magic_power": round(lerp_curve(ct_magic_power, will), 1),
        "manual_dexterity_pct": round(lerp_curve(ct_manual_dex, dexterity) * 100, 1),
        "equip_speed_pct": round(lerp_curve(ct_equip_speed, dexterity) * 100, 1),
        "buff_duration_pct": round(lerp_curve(ct_buff_dur, will) * 100, 1),
        "debuff_duration_pct": round(lerp_curve(ct_debuff_dur, will) * 100, 1),
        "regular_interaction_speed_pct": round(lerp_curve(ct_interact, resourcefulness) * 100, 1),
        "health_recovery_bonus_pct": round(lerp_curve(ct_recovery, resourcefulness) * 100, 1),
        "physical_damage_reduction_pct": phys_dmg_reduction_pct,
        "physical_power_bonus_pct": round(lerp_curve(ct_phys_dmg_mod, strength) * 100, 1),
        "magic_power_bonus_pct": round(lerp_curve(ct_mag_dmg_mod, will) * 100, 1),
        "magical_interaction_speed_pct": round(lerp_curve(ct_mag_interact, will) * 100, 1),
        "spell_recovery_bonus_pct": round(lerp_curve(ct_spell_recovery, knowledge) * 100, 1),
        "persuasiveness": round(lerp_curve(ct_persuasiveness, resourcefulness), 1),
        "cooldown_reduction_pct": round(lerp_curve(ct_cooldown, resourcefulness) * 100, 1),
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


# ═══════════════════════════════════════════════════════════════════════
# SECTION: Description Resolution
# Resolves placeholder tags in ability descriptions (e.g., <Duration>,
# <Constant>, <PropertyName>, <GEMod>, <Exec.PropertyName>) by loading
# _Desc.json files and their referenced effect/constant/modifier data.
# ═══════════════════════════════════════════════════════════════════════


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


def _extract_asset_name(ref):
    """Extract the asset ID name from a _Desc.json ObjectName field.

    ObjectName looks like: "DCGEModifierDataAsset'Id_GEModifier_HeavySwing'"
    Returns: "Id_GEModifier_HeavySwing"
    """
    obj_name = ref.get("ObjectName", "")
    m = re.search(r"'([^']+)'", obj_name)
    return m.group(1) if m else ""


def _load_desc_file(desc_path):
    """Load a _Desc.json file and return (effects, constants, gemodifiers, skill_spell_data, movementmodifiers)."""
    data = load_json_silent(desc_path)
    if data is None:
        return [], [], [], [], [], []
    if isinstance(data, list) and len(data) > 0:
        props = data[0].get("Properties", {})
    elif isinstance(data, dict):
        props = data.get("Properties", {})
    else:
        return [], [], [], [], [], []

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

    # GEModifiers: store (asset_name, props) tuples so we can look up values
    gemodifiers = []
    for ref in props.get("GEModifierDataAssetArray", []):
        asset_name = _extract_asset_name(ref)
        obj_path = ref.get("ObjectPath", "")
        gemod_props = _load_effect_file(obj_path)
        gemodifiers.append((asset_name, gemod_props if gemod_props else {}))

    # Skill/Spell metadata (range, casting time, channeling duration)
    skill_spell_data = []
    for key in ("SkillDataAssetArray", "SpellDataAssetArray"):
        for ref in props.get(key, []):
            obj_path = ref.get("ObjectPath", "")
            ss_props = _load_effect_file(obj_path)
            skill_spell_data.append(ss_props if ss_props else {})

    # MovementModifiers: load the JSON data directly (not binary)
    movementmodifiers = []
    for ref in props.get("MovementModifierDataAssetArray", []):
        obj_path = ref.get("ObjectPath", "")
        mm_props = _load_effect_file(obj_path)
        movementmodifiers.append(mm_props if mm_props else {})

    # Perk metadata (Radius / AreaRadius)
    perk_data = []
    for ref in props.get("PerkDataAssetArray", []):
        obj_path = ref.get("ObjectPath", "")
        perk_props = _load_effect_file(obj_path)
        perk_data.append(perk_props if perk_props else {})

    return effects, constants, gemodifiers, skill_spell_data, movementmodifiers, perk_data


def _get_gemod_value(gemodifiers, index):
    """Get the float value for a GEModifier at the given index.

    Uses GEMODIFIER_VALUES dict (extracted from binary .uexp) because the
    JSON exports have corrupted float fields.
    """
    if index < 0 or index >= len(gemodifiers):
        return None
    asset_name, _props = gemodifiers[index]
    if asset_name in GEMODIFIER_VALUES:
        return GEMODIFIER_VALUES[asset_name]
    return None


def _apply_gemod_format(value, fmt, mod_type):
    """Apply GEMod/MovementMod format conversion to a float value.

    For Type="Add", the value is an additive modifier (effective = 1.0 + value).
    For Type="Multiply", the value is a direct multiplier.

    Format rules:
      AbsFromZero:  |value| * 100
      AbsFromOne:   |effective - 1| * 100
      FromOne:      (effective - 1) * 100
      FromZero:     effective * 100
      (no format):  return value as-is (e.g., seconds or multiplier)
    """
    if mod_type == "Add":
        effective = 1.0 + value
    else:
        effective = value

    if not fmt:
        return effective
    if fmt == "AbsFromZero":
        return abs(value) * 100
    if fmt == "AbsFromOne":
        return abs(effective - 1.0) * 100
    if fmt == "FromOne":
        return (effective - 1.0) * 100
    if fmt == "FromZero":
        return effective * 100
    return effective


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
        # Fallback to hardcoded Blueprint values
        return BLUEPRINT_HARDCODED.get(prop_name)
    val = effects[index].get(prop_name)
    if val is not None:
        return val
    # Special case: AllAttributes is virtual - check individual base stats
    if prop_name in ("AllAttributes", "AllAttributesMod"):
        # Try Base keys first, then Mod keys
        base_keys = ["StrengthBase", "VigorBase", "AgilityBase", "DexterityBase",
                      "WillBase", "KnowledgeBase", "ResourcefulnessBase"]
        mod_keys = ["StrengthMod", "VigorMod", "AgilityMod", "DexterityMod",
                     "WillMod", "KnowledgeMod", "ResourcefulnessMod"]
        for keys in [base_keys, mod_keys]:
            vals = [effects[index].get(k) for k in keys]
            real_vals = [v for v in vals if v is not None]
            if real_vals and all(v == real_vals[0] for v in real_vals):
                return real_vals[0]
    # Fallback to hardcoded Blueprint values
    return BLUEPRINT_HARDCODED.get(prop_name)


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


def _display_name(prop_name):
    """Get the human-readable display name for a property tag name."""
    if prop_name in PROPERTY_DISPLAY_NAMES:
        return PROPERTY_DISPLAY_NAMES[prop_name]
    # Fallback: CamelCase to spaced words
    return to_display_name(prop_name)


def resolve_description(raw_desc, desc_path):
    """Resolve description placeholders using effect/constant data from _Desc.json.

    Handles tag patterns:
      <Constant Type="Float" Format="FromZero">[N]%</>  -> constants[N].FloatValue * 100
      <Constant Type="Float">[N]%</>                    -> constants[N].FloatValue * 100
      <Constant Type="float" Format="FromOne">[N]%</>   -> abs(constants[N].FloatValue - 1) * 100
      <Constant Type="Float" Format="AbsFromZero">[N]%</>  -> abs(constants[N].FloatValue) * 100
      <Constant Type="Integer">[N]</>                   -> constants[N].IntValue or FloatValue as int
      <Constant Type="float" Format="Normal">[N]</>     -> constants[N].FloatValue as-is
      <Duration>[N] seconds</>                          -> effects[N].Duration / 1000
      <Duration>[N]</>                                  -> effects[N].Duration / 1000
      <PropertyName>[N]% _</>                           -> effects[N].PropertyName scaled
      <PropertyName>[N] _</>                            -> effects[N].PropertyName scaled
      <PropertyName>_ by [N]%</>                        -> display_name by value%
      <PropertyName>[N1]/[N2]/[N3] _</>                 -> val1/val2/val3
      <GEMod Type="..." Format="...">[N]%</>            -> gemodifiers[N] with format conversion
      <Exec.PropertyName>[N]</>                         -> effects[N].ExecPropertyName
      <Exec.PropertyName>[N] _</>                       -> value + display name
      <Skill Type="Range">[N]m</>                       -> skill/spell metadata
      <Spell Type="AreaRadius">[N]m</>                  -> skill/spell metadata
      <MeleeAttack Type="..." Format="...">[N]%</>      -> melee attack data
      <MovementMod Type="..." Format="...">[N]%</>      -> movementmodifiers[N] with format conversion
      <YellowColor>text</>                              -> text (just strip tags)
      <BurnEffect>text</>                               -> text
      <PropertyName>_</>                                -> display name of property
      <PropertyName>_ text</>                           -> display name + text
    """
    if not raw_desc:
        return raw_desc

    effects, constants, gemodifiers, skill_spell_data, movementmodifiers, perk_data = _load_desc_file(desc_path)

    text = raw_desc

    # --- Skill/Spell metadata tags ---
    # <Skill Type="Range">[N]m</>, <Spell Type="AreaRadius">[N]m radius</>
    # <Skill Type="CastingTime">[N] seconds</>, <Spell Type="ChannelingDuration">[N] seconds</>
    # These reference skill/spell data properties
    _metadata_field_map = {
        "Range": ("Range", 100.0),           # divide by 100 for meters
        "AreaRadius": ("AreaRadius", 100.0),  # divide by 100 for meters
        "CastingTime": ("CastingTime", 1.0),  # seconds as-is
        "ChannelingDuration": ("ChannelingDuration", 1.0),
    }
    # Perk data uses different property names
    _perk_field_map = {
        "AreaRadius": ("Radius", 100.0),    # Perk "Radius" -> AreaRadius, divide by 100
        "Range": ("Radius", 100.0),
    }

    def replace_skill_spell_meta(m):
        tag_type = m.group("tag")
        field = m.group("field")
        idx = int(m.group("idx"))
        suffix = m.group("suffix")
        if tag_type == "Perk":
            # Look up in perk_data array
            field_map = _perk_field_map
            data_array = perk_data
        else:
            field_map = _metadata_field_map
            data_array = skill_spell_data
        if field in field_map:
            prop_key, divisor = field_map[field]
            if idx < len(data_array) and data_array[idx]:
                val = data_array[idx].get(prop_key)
                if val is not None:
                    scaled = val / divisor if divisor != 1.0 else val
                    return _format_number(scaled) + suffix
        return "[" + str(idx) + "]" + suffix

    text = re.sub(
        r'<(?P<tag>Skill|Spell|Perk)\s+Type="(?P<field>[^"]+)">\[(?P<idx>\d+)\](?P<suffix>[^<]*)</>',
        replace_skill_spell_meta, text
    )

    # --- Constant tags ---

    # 1a. <Constant Type="Float" Format="FromZero">[N]%</>
    def replace_constant_from_zero(m):
        idx = int(m.group("idx"))
        suffix = m.group("suffix")
        if idx < len(constants) and constants[idx]:
            val = constants[idx].get("FloatValue", 0)
            formatted = _format_number(abs(val) * 100)
            return formatted + suffix
        return m.group(0)

    text = re.sub(
        r'<Constant\s+[^>]*?Format="(?:FromZero|AbsFromZero)"[^>]*>\[(?P<idx>\d+)\](?P<suffix>[^<]*)</>',
        replace_constant_from_zero, text
    )

    # 1b. <Constant Type="float" Format="FromOne">[N]%</>
    def replace_constant_from_one(m):
        idx = int(m.group("idx"))
        suffix = m.group("suffix")
        if idx < len(constants) and constants[idx]:
            val = constants[idx].get("FloatValue", 0)
            formatted = _format_number(abs(val - 1.0) * 100)
            return formatted + suffix
        return m.group(0)

    text = re.sub(
        r'<Constant\s+[^>]*?Format="FromOne"[^>]*>\[(?P<idx>\d+)\](?P<suffix>[^<]*)</>',
        replace_constant_from_one, text
    )

    # 1c. <Constant Type="Integer">[N]</>
    def replace_constant_integer(m):
        idx = int(m.group("idx"))
        suffix = m.group("suffix")
        if idx < len(constants) and constants[idx]:
            val = constants[idx].get("Int32Value", constants[idx].get("IntValue", constants[idx].get("FloatValue", 0)))
            formatted = _format_number(int(val) if isinstance(val, float) else val)
            return formatted + suffix
        return m.group(0)

    text = re.sub(
        r'<Constant\s+[^>]*?Type="Integer"[^>]*>\[(?P<idx>\d+)\](?P<suffix>[^<]*)</>',
        replace_constant_integer, text
    )

    # 1d. <Constant Type="float" Format="Normal">[N]</>
    def replace_constant_normal(m):
        idx = int(m.group("idx"))
        suffix = m.group("suffix")
        if idx < len(constants) and constants[idx]:
            val = constants[idx].get("FloatValue", 0)
            formatted = _format_number(val)
            return formatted + suffix
        return m.group(0)

    text = re.sub(
        r'<Constant\s+[^>]*?Format="Normal"[^>]*>\[(?P<idx>\d+)\](?P<suffix>[^<]*)</>',
        replace_constant_normal, text
    )

    # 1e. Generic <Constant Type="Float">[N]...</> (no format)
    def replace_constant_plain(m):
        idx = int(m.group("idx"))
        suffix = m.group("suffix")
        if idx < len(constants) and constants[idx]:
            val = constants[idx].get("FloatValue", 0)
            if "%" in suffix:
                # If value > 1, it's already a percentage (e.g., 50.0 = 50%)
                # If value <= 1, it's a ratio (e.g., 0.4 = 40%)
                formatted = _format_number(abs(val) if abs(val) > 1 else abs(val) * 100)
            else:
                formatted = _format_number(val)
            return formatted + suffix
        return m.group(0)

    text = re.sub(
        r'<Constant\s+Type="[Ff]loat">\[(?P<idx>\d+)\](?P<suffix>[^<]*)</>',
        replace_constant_plain, text
    )

    # --- Duration tags ---

    # 2. <Duration>[N] seconds</> and <Duration>[N]</>
    #    Also handle multi-index: <Duration>[N1]/[N2]/[N3] seconds</>
    def replace_duration_multi(m):
        indices_str = m.group("indices")
        suffix = m.group("suffix")
        indices = [int(x) for x in re.findall(r'\[(\d+)\]', indices_str)]
        values = []
        for idx in indices:
            val = _get_effect_value(effects, idx, "Duration")
            if val is not None:
                values.append(_format_number(val / 1000.0))
            else:
                values.append(f"[{idx}]")
        return "/".join(values) + suffix

    text = re.sub(
        r'<Duration>(?P<indices>(?:\[\d+\]/?)+)(?P<suffix>[^<]*)</>',
        replace_duration_multi, text
    )

    # --- GEMod tags: resolve using GEMODIFIER_VALUES ---
    def replace_gemod(m):
        attrs = m.group("attrs")
        idx = int(m.group("idx"))
        suffix = m.group("suffix")
        # Parse Type and Format from attributes
        type_m = re.search(r'Type="([^"]+)"', attrs)
        fmt_m = re.search(r'Format="([^"]+)"', attrs)
        mod_type = type_m.group(1) if type_m else "Multiply"
        fmt = fmt_m.group(1) if fmt_m else ""
        value = _get_gemod_value(gemodifiers, idx)
        if value is not None:
            display = _apply_gemod_format(value, fmt, mod_type)
            return _format_number(display) + suffix
        return "[" + str(idx) + "]" + suffix

    text = re.sub(
        r'<GEMod\s+(?P<attrs>[^>]*)>\[(?P<idx>\d+)\](?P<suffix>[^<]*)</>',
        replace_gemod, text
    )
    # Fallback: strip any remaining GEMod tags that didn't match the pattern
    text = re.sub(
        r'<GEMod\s+[^>]*>([^<]*)</>',
        r'\1', text
    )

    # --- MovementMod tags: resolve using MovementModifier JSON data ---
    def replace_movementmod(m):
        attrs = m.group("attrs")
        idx = int(m.group("idx"))
        suffix = m.group("suffix")
        # Parse Type (Multiply/JumpZMultiply) and Format from attributes
        type_m = re.search(r'Type="([^"]+)"', attrs)
        fmt_m = re.search(r'Format="([^"]+)"', attrs)
        prop_type = type_m.group(1) if type_m else "Multiply"
        fmt = fmt_m.group(1) if fmt_m else ""
        if idx < len(movementmodifiers) and movementmodifiers[idx]:
            value = movementmodifiers[idx].get(prop_type)
            if value is not None:
                # MovementMod values are always direct multipliers (not additive)
                display = _apply_gemod_format(value, fmt, "Multiply")
                return _format_number(display) + suffix
        return "[" + str(idx) + "]" + suffix

    text = re.sub(
        r'<MovementMod\s+(?P<attrs>[^>]*)>\[(?P<idx>\d+)\](?P<suffix>[^<]*)</>',
        replace_movementmod, text
    )

    # --- MeleeAttack tags: resolve DamageRatio from MeleeAttack data ---
    def replace_meleeattack(m):
        attrs = m.group("attrs")
        idx = int(m.group("idx"))
        suffix = m.group("suffix")
        type_m = re.search(r'Type="([^"]+)"', attrs)
        fmt_m = re.search(r'Format="([^"]+)"', attrs)
        prop_type = type_m.group(1) if type_m else ""
        fmt = fmt_m.group(1) if fmt_m else ""
        # Look for MeleeAttack data in skill_spell_data or search known files
        # Whirlwind uses DamageRatio=0.8 uniformly across all weapon types
        if prop_type == "DamageRatio":
            # Search for a MeleeAttack file matching the desc file name
            desc_stem = desc_path.stem.replace("_Desc", "")
            melee_pattern = f"Id_MeleeAttack_GA_*{desc_stem}*.json"
            value = None
            for melee_file in MELEE_ATTACK_DIR.glob(melee_pattern):
                melee_data = load_json_silent(melee_file)
                if melee_data and isinstance(melee_data, list) and melee_data:
                    value = melee_data[0].get("Properties", {}).get("DamageRatio")
                    if value is not None:
                        break
            if value is not None:
                display = _apply_gemod_format(value, fmt, "Multiply")
                return _format_number(display) + suffix
        return "[" + str(idx) + "]" + suffix

    text = re.sub(
        r'<MeleeAttack\s+(?P<attrs>[^>]*)>\[(?P<idx>\d+)\](?P<suffix>[^<]*)</>',
        replace_meleeattack, text
    )

    # --- Remaining metadata tags: Perk Type="..." ---
    # Strip tags, keep content (Skill/Spell metadata already handled above)
    text = re.sub(
        r'<(?:Skill|Spell|Perk|MeleeAttack|MovementMod)\s+[^>]*>([^<]*)</>',
        r'\1', text
    )

    # --- Exec.PropertyName tags ---

    # 4a. <Exec.PropertyName>[N1]/[N2]/[N3] suffix</> (multi-index exec)
    def replace_exec_multi(m):
        prop_name = m.group("prop")
        indices_str = m.group("indices")
        suffix = m.group("suffix")
        exec_key = "Exec" + prop_name
        indices = [int(x) for x in re.findall(r'\[(\d+)\]', indices_str)]
        values = []
        for idx in indices:
            found_key = exec_key
            val = _get_effect_value(effects, idx, exec_key)
            if val is None:
                found_key = prop_name
                val = _get_effect_value(effects, idx, prop_name)
                # Also try fallbacks
                if val is None:
                    fallbacks = PROPERTY_NAME_FALLBACKS.get(prop_name, [])
                    for fb in fallbacks:
                        val = _get_effect_value(effects, idx, fb)
                        if val is not None:
                            found_key = fb
                            break
            if val is not None:
                scaled = _scale_property(found_key, val)
                values.append(_format_number(scaled))
            else:
                values.append(f"[{idx}]")
        result = "/".join(values)
        has_label = "_" in suffix
        clean_suffix = suffix.replace(" _", "").replace("_", "").strip()
        if has_label:
            prop_display = _display_name(prop_name)
            if clean_suffix:
                return result + " " + clean_suffix + " " + prop_display
            return result + " " + prop_display
        if clean_suffix:
            return result + " " + clean_suffix
        return result

    text = re.sub(
        r'<Exec\.(?P<prop>\w+)>(?P<indices>(?:\[\d+\]/)+\[\d+\])(?P<suffix>[^<]*)</>',
        replace_exec_multi, text
    )

    # 4b-pre. <Exec.PropertyName>prefix [N]suffix</> (prefix text before index, e.g., " * [1]%")
    def replace_exec_with_prefix(m):
        prop_name = m.group("prop")
        prefix = m.group("prefix")
        idx = int(m.group("idx"))
        suffix = m.group("suffix")
        exec_key = "Exec" + prop_name
        found_key = exec_key
        val = _get_effect_value(effects, idx, exec_key)
        if val is None:
            found_key = prop_name
            val = _get_effect_value(effects, idx, prop_name)
        if val is None:
            fallbacks = PROPERTY_NAME_FALLBACKS.get(prop_name, [])
            for fb in fallbacks:
                val = _get_effect_value(effects, idx, fb)
                if val is not None:
                    found_key = fb
                    break
        if val is not None:
            scaled = _scale_property(found_key, val)
            formatted = _format_number(scaled)
            return prefix.strip() + " " + formatted + suffix
        return m.group(0)

    text = re.sub(
        r'<Exec\.(?P<prop>\w+)>(?P<prefix>[^<\[]+)\[(?P<idx>\d+)\](?P<suffix>[^<]*)</>',
        replace_exec_with_prefix, text
    )

    # 4b. <Exec.PropertyName>[N] suffix</> (single index exec)
    def replace_exec_prop(m):
        prop_name = m.group("prop")
        idx = int(m.group("idx"))
        suffix = m.group("suffix")
        exec_key = "Exec" + prop_name
        found_key = exec_key
        val = _get_effect_value(effects, idx, exec_key)
        if val is None:
            found_key = prop_name
            val = _get_effect_value(effects, idx, prop_name)
        if val is None:
            fallbacks = PROPERTY_NAME_FALLBACKS.get(prop_name, [])
            for fb in fallbacks:
                val = _get_effect_value(effects, idx, fb)
                if val is not None:
                    found_key = fb
                    break
        if val is not None:
            scaled = _scale_property(found_key, val)
            formatted = _format_number(scaled)
            has_label = "_" in suffix
            clean_suffix = suffix.replace(" _", "").replace("_", "").strip()
            if has_label:
                prop_display = _display_name(prop_name)
                if clean_suffix:
                    return formatted + " " + clean_suffix + " " + prop_display
                return formatted + " " + prop_display
            if clean_suffix:
                return formatted + " " + clean_suffix
            return formatted
        return m.group(0)

    text = re.sub(
        r'<Exec\.(?P<prop>\w+)>\[(?P<idx>\d+)\](?P<suffix>[^<]*)</>',
        replace_exec_prop, text
    )

    # --- Property tags with _ before [N] ---
    # 5a. <PropertyName>_ by [N1]/[N2]/[N3]%</> or <PropertyName>_ by [N]%</> (label then value)
    def replace_label_then_value(m):
        prop_name = m.group("prop")
        prefix_text = m.group("prefix")
        indices_and_suffix = m.group("rest")
        # Extract all indices from the rest
        indices = [int(x) for x in re.findall(r'\[(\d+)\]', indices_and_suffix)]
        # Extract suffix after last index
        suffix = re.sub(r'(?:\[\d+\]/?)+', '', indices_and_suffix, count=1)
        # Remove leading separators
        suffix = re.sub(r'^/+', '', suffix)

        values = []
        for idx in indices:
            val = _get_effect_value(effects, idx, prop_name)
            if val is None:
                fallbacks = PROPERTY_NAME_FALLBACKS.get(prop_name, [])
                for fb in fallbacks:
                    val = _get_effect_value(effects, idx, fb)
                    if val is not None:
                        break
            if val is not None:
                scaled = _scale_property(prop_name, val)
                values.append(_format_number(abs(scaled)))
            else:
                values.append(f"[{idx}]")

        result = "/".join(values)
        prop_display = _display_name(prop_name)
        clean_prefix = prefix_text.replace("_", "").strip()
        clean_suffix = suffix.strip()
        if clean_prefix:
            return prop_display + " " + clean_prefix + " " + result + clean_suffix
        return prop_display + " " + result + clean_suffix

    text = re.sub(
        r'<(?P<prop>[A-Za-z]\w+)>(?P<prefix>[^<\[]*_[^<\[]*)(?P<rest>(?:\[\d+\]/?)+[^<]*)</>',
        replace_label_then_value, text
    )

    # --- Multi-index property tags ---
    # 6. <PropertyName>[N1]/[N2]/[N3] _</> or <PropertyName>[N1]/[N2]/[N3]% _</>
    def replace_multi_index(m):
        prop_name = m.group("prop")
        indices_str = m.group("indices")
        suffix = m.group("suffix")
        indices = [int(x) for x in re.findall(r'\[(\d+)\]', indices_str)]
        values = []
        for idx in indices:
            val = _get_effect_value(effects, idx, prop_name)
            if val is None:
                fallbacks = PROPERTY_NAME_FALLBACKS.get(prop_name, [])
                for fb in fallbacks:
                    val = _get_effect_value(effects, idx, fb)
                    if val is not None:
                        break
            if val is not None:
                scaled = _scale_property(prop_name, val)
                values.append(_format_number(scaled))
            else:
                values.append(f"[{idx}]")
        result = "/".join(values)
        has_label = "_" in suffix
        clean_suffix = suffix.replace(" _", "").replace("_", "").strip()
        if has_label:
            prop_display = _display_name(prop_name)
            if clean_suffix:
                return result + clean_suffix + " " + prop_display
            return result + " " + prop_display
        if clean_suffix:
            return result + " " + clean_suffix
        return result

    text = re.sub(
        r'<(?P<prop>[A-Za-z]\w+)>(?P<indices>(?:\[\d+\]/)+\[\d+\])(?P<suffix>[^<]*)</>',
        replace_multi_index, text
    )

    # --- Single-index property tags ---
    # 7. <PropertyName>[N]% _</> and <PropertyName>[N] _</>
    def replace_property_with_index(m):
        prop_name = m.group("prop")
        idx = int(m.group("idx"))
        suffix = m.group("suffix")
        val = _get_effect_value(effects, idx, prop_name)
        if val is None:
            fallbacks = PROPERTY_NAME_FALLBACKS.get(prop_name, [])
            for fb in fallbacks:
                val = _get_effect_value(effects, idx, fb)
                if val is not None:
                    break
        if val is not None:
            scaled = _scale_property(prop_name, val)
            formatted = _format_number(scaled)
            has_label = "_" in suffix
            clean_suffix = suffix.replace(" _", "").replace("_", "").strip()
            if has_label:
                prop_display = _display_name(prop_name)
                if clean_suffix:
                    return formatted + clean_suffix + " " + prop_display
                return formatted + " " + prop_display
            if clean_suffix:
                return formatted + clean_suffix
            return formatted
        return m.group(0)

    text = re.sub(
        r'<(?P<prop>[A-Za-z]\w+)>\s*[+\-]?\[(?P<idx>\d+)\](?P<suffix>[^<]*)</>',
        replace_property_with_index, text
    )

    # --- Color/Effect tags: strip, keep inner text ---
    text = re.sub(r'<YellowColor>([^<]*)</>', r'\1', text)
    text = re.sub(r'<(?:BurnEffect|WetEffect|ElectrifiedEffect|Burn)>([^<]*)</>', r'\1', text)

    # --- Label-only property tags ---
    # 8. <PropertyName>_</> or <PropertyName>text</> (no [N] index)
    def replace_label_tag(m):
        prop_name = m.group("prop")
        inner = m.group("inner").strip()
        if inner == "_" or inner == "":
            return _display_name(prop_name)
        # If content is just _ with some text around it
        clean = inner.replace("_", "").strip()
        if "_" in inner:
            # Has both _ and other text (rare)
            display = _display_name(prop_name)
            if clean:
                return display + " " + clean
            return display
        # No underscore, just text (like <BurnEffect>burns</>)
        return clean if clean else _display_name(prop_name)

    text = re.sub(
        r'<(?P<prop>[A-Za-z]\w+)>(?P<inner>[^<\[]*)</>',
        replace_label_tag, text
    )

    # --- Exec label-only tags ---
    text = re.sub(
        r'<Exec\.(\w+)>([^<\[]*)</>',
        lambda m: _display_name(m.group(1)) if m.group(2).strip() in ("_", "") else m.group(2).replace("_", "").strip(),
        text
    )

    # --- Final cleanup ---
    text = re.sub(r'</>', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'  +', ' ', text)
    text = re.sub(r' +([,.])', r'\1', text)
    text = text.strip()

    return text


def _find_desc_path_perk(short_name):
    """Find the _Desc.json file for a perk."""
    # Primary path: folder matches perk name
    primary = PERK_DESC_DIR / short_name / f"{short_name}_Desc.json"
    if primary.exists():
        return primary
    # Search all subdirectories for the desc file (handles folder name mismatches)
    for desc_file in PERK_DESC_DIR.glob(f"*/{short_name}_Desc.json"):
        return desc_file
    return primary  # Return primary path even if not found (caller checks existence)


def _find_desc_path_skill(short_name):
    """Find the _Desc.json file for a skill."""
    primary = SKILL_DESC_DIR / f"{short_name}_Desc.json"
    if primary.exists():
        return primary
    # Try variant: CutThroat -> CutThroat_Skill, Caltrops -> Caltrop
    for desc_file in SKILL_DESC_DIR.glob("*_Desc.json"):
        stem = desc_file.stem.replace("_Desc", "").replace("_Skill", "")
        if stem.lower() == short_name.lower() or stem.lower() == short_name.lower().rstrip("s"):
            return desc_file
    # Try with "of" variant
    alt_name = short_name.replace("Of", "of")
    alt_path = SKILL_DESC_DIR / f"{alt_name}_Desc.json"
    if alt_path.exists():
        return alt_path
    return primary


def _find_desc_path_spell(short_name):
    """Find the _Desc.json file for a spell."""
    primary = SPELL_DESC_DIR / f"{short_name}_Desc.json"
    if primary.exists():
        return primary
    # Try case-insensitive and variant name matching
    # e.g., Explosion -> ExplosionSpell, LocustSwarm -> LocustsSwarm
    lower_name = short_name.lower()
    for desc_file in SPELL_DESC_DIR.glob("*_Desc.json"):
        stem = desc_file.stem.replace("_Desc", "")
        if stem.lower().startswith(lower_name) or lower_name.startswith(stem.lower()):
            return desc_file
    # Try with "of" case variants: PowerOfSacrifice -> PowerofSacrifice
    alt_name = short_name.replace("Of", "of")
    alt_path = SPELL_DESC_DIR / f"{alt_name}_Desc.json"
    if alt_path.exists():
        return alt_path
    return primary


def _find_desc_path_music(short_name):
    """Find the _Desc.json file for a music/song."""
    return MUSIC_DESC_DIR / f"{short_name}_Desc.json"


def _find_desc_path_shapeshift(short_name):
    """Find the _Desc.json file for a shapeshift."""
    return SHAPESHIFT_DESC_DIR / f"ShapeShift{short_name}_Desc.json"


def get_description(short_name, loc, desc_path):
    """Get the localized description for an ability, handling typos and hardcodes.

    Checks DESCRIPTION_HARDCODES first (for abilities with no localization entry),
    then DESCRIPTION_KEY_OVERRIDES (for abilities whose Game.json keys have typos),
    then falls back to the standard key pattern.
    """
    # Check hardcoded descriptions first (no localization entry at all)
    if short_name in DESCRIPTION_HARDCODES:
        return DESCRIPTION_HARDCODES[short_name]

    # Check key overrides for typos in Game.json
    if short_name in DESCRIPTION_KEY_OVERRIDES:
        override_key = DESCRIPTION_KEY_OVERRIDES[short_name]
        raw_desc = loc.get(override_key, "")
        if raw_desc:
            return try_resolve_description(raw_desc, desc_path)

    # Standard key pattern
    desc_key = f"Text_DataAsset_{short_name}_Desc_{short_name}Desc"
    raw_desc = loc.get(desc_key, "")
    return try_resolve_description(raw_desc, desc_path)


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


# ═══════════════════════════════════════════════════════════════════════
# SECTION: Shapeshift Data Helpers
# Reads stat modifiers and form skills from ShapeShift StatusEffect and
# raw ShapeShift V2 files for Druid forms.
# ═══════════════════════════════════════════════════════════════════════


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


# ═══════════════════════════════════════════════════════════════════════
# SECTION: Bard Song Performance Tiers
# Reads tier-specific effects (Bad/Good/Perfect) from ActorStatusEffect
# and MusicEffect files. Scales property values for display.
# ═══════════════════════════════════════════════════════════════════════


def _scale_tier_property(prop_name, raw_value):
    """Apply the correct scale conversion to a tier effect property value.

    Uses the same DIV10_PROPERTIES set as description scaling.
    Duration is kept as-is in ms (frontend formats it).
    """
    if raw_value is None:
        return None
    if prop_name == "duration_ms":
        return raw_value
    if prop_name in DIV10_PROPERTIES:
        return raw_value / 10.0
    return raw_value


def _collect_effect_props(data):
    """Extract gameplay properties from an effect data file, skipping metadata keys."""
    if data is None:
        return {}
    props = data[0].get("Properties", {}) if isinstance(data, list) and data else {}
    skip_keys = {"EffectClass", "EventTag", "TargetType", "Duration",
                 "AssetTags", "V1Data"}
    result = {}
    duration = props.get("Duration")
    if duration is not None:
        result["duration_ms"] = duration
    for key, val in props.items():
        if key not in skip_keys and not isinstance(val, (dict, list)):
            result[key] = val
    return result


def _read_song_tier_effects(short_name):
    """Read tier-specific effects for a Bard song.

    For buff songs: look for ActorStatusEffect_{short_name}_{Bad|Good|Perfect}
    Also merges "{short_name}Granted_{tier}" variants which contain the actual
    gameplay properties (e.g., AllegroGranted_Bad has ActionSpeed/SpellCastingSpeed
    while Allegro_Bad only has Duration).

    For damage songs: look for MusicEffect_{short_name}_{Bad|Good|Perfect}

    All properties are scaled using _scale_tier_property (DIV10 for %, raw for flat).
    """
    tier_effects = {}
    tiers = ["Bad", "Good", "Perfect"]

    for tier in tiers:
        tier_data = {}

        # Try ActorStatusEffect (buff songs) - base file has duration
        se_path = STATUS_EFFECT_DIR / f"Id_ActorStatusEffect_{short_name}_{tier}.json"
        se_data = load_json_silent(se_path)
        if se_data is not None:
            tier_data.update(_collect_effect_props(se_data))

        # Merge Granted variant (has the actual gameplay properties)
        granted_path = STATUS_EFFECT_DIR / f"Id_ActorStatusEffect_{short_name}Granted_{tier}.json"
        granted_data = load_json_silent(granted_path)
        if granted_data is not None:
            granted_props = _collect_effect_props(granted_data)
            # Merge: granted properties override base, but keep duration from base
            for key, val in granted_props.items():
                if key == "duration_ms" and "duration_ms" in tier_data:
                    continue  # Keep the duration from the base effect
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

        # Scale all properties
        if tier_data:
            scaled = {}
            for key, val in tier_data.items():
                if isinstance(val, (int, float)):
                    scaled[key] = _scale_tier_property(key, val)
                else:
                    scaled[key] = val
            tier_effects[tier.lower()] = scaled

    return tier_effects if tier_effects else None


# ═══════════════════════════════════════════════════════════════════════
# SECTION: Perk Conditions
# Extracts activation conditions from GE_*.json files (tag requirements
# like "Requires sword equipped") and maps gameplay tags to readable text.
# ═══════════════════════════════════════════════════════════════════════

TAG_TO_CONDITION = {
    "Type.Item.Weapon.Sword": "Requires sword equipped",
    "Type.Item.Weapon.Axe": "Requires axe equipped",
    "Type.Item.Weapon.Crossbow": "Requires crossbow equipped",
    "Type.Item.Weapon.Bow": "Requires bow equipped",
    "Type.Item.Weapon.Staff": "Requires staff equipped",
    "Type.Item.Weapon.Dagger": "Requires dagger equipped",
    "Type.Item.Weapon.Mace": "Requires mace equipped",
    "Type.Item.Weapon.Polearm": "Requires polearm equipped",
    "Type.Item.Weapon": "Requires weapon equipped",
    "Type.Item.Shield": "Requires shield equipped",
    "Type.Item.Armor": "Requires armor equipped",
    "Type.Item.Hand.TwoHanded": "Requires two-handed weapon",
    "Type.Item.Slot.Primary": "Requires primary slot",
    "Type.Item.Utility.MusicalInstrument": "Requires musical instrument equipped",
    "Type.Item.Utility.Installable.CampfireKit": "Requires campfire kit",
    "Type.Item.Utility.Installable.Trap": "Requires trap equipped",
    "Id.Item.Rapier": "Requires Rapier equipped",
    "Id.Item.DemonsGlee": "Requires Demon's Glee equipped",
    "Id.Item.HandCrossbow": "Requires Hand Crossbow equipped",
    "State.Character.Act.Defending": "Active while blocking",
    "State.Character.Act.Defending.Weapon": "Active while weapon blocking",
    "State.Character.Act.Defending.Weapon.Sword": "Active while sword blocking",
    "State.Character.Act.Attack.Melee": "Active during melee attack",
    "State.Character.Act.Attack.Melee.Dagger": "Active during dagger melee attack",
    "State.Character.Act.Attack.Melee.Axe": "Active during axe melee attack",
    "State.Character.Act.Attack.Melee.MusicalInstrument": "Active during instrument melee attack",
    "State.Character.Act.Attack.Ranged": "Active during ranged attack",
    "State.Character.Act.Attack.Ranged.Axe": "Active during axe ranged attack",
    "State.Character.Act.Attack.Ranged.Dagger": "Active during dagger ranged attack",
    "State.Character.Act.Attack.Ranged.MusicalInstrument": "Active during instrument ranged attack",
    "State.Character.Act.Attack.Ranged.Throwable": "Active during thrown attack",
    "State.Character.Act.Attack.Special": "Active during special attack",
    "State.Character.Act.SpellCast": "Active while casting",
    "State.Character.Act.SpellDualCast": "Active while dual casting",
    "State.Character.Act.SpellDualCast.Merge": "Active while merge casting",
    "State.Character.Act.SpellDualCast.Primary": "Active while primary casting",
    "State.Character.Act.SpellDualCast.Secondary": "Active while secondary casting",
    "State.Character.Act.PlayMusic": "Active while playing music",
    "State.Character.Act.Hide": "Active while hidden",
    "State.Character.Act.Interact.Install": "Active while installing",
    "State.Character.Act.React.Block": "Active on block reaction",
    "State.ActorStatus.Buff.ShapeShift.Animal": "Active in animal form",
    "State.ActorStatus.Buff.SacredWater": "Active with Holy Water buff",
    "State.Special.WeaponMasteryBasedAct": "Active during weapon mastery action",
    "Type.Spell.Source.Divine.Resurrection": "Active with resurrection spell",
    "Type.Spell.Source.Spirit": "Active with spirit spell",
}


def _tag_to_condition(tag):
    """Convert a gameplay tag to a human-readable condition string."""
    if tag in TAG_TO_CONDITION:
        return TAG_TO_CONDITION[tag]
    # Fallback: extract last 2 segments
    parts = tag.split(".")
    if len(parts) >= 2:
        return f"Requires: {'.'.join(parts[-2:])}"
    return f"Requires: {tag}"


def extract_perk_conditions(perk_id):
    """Extract activation conditions from GE_*.json files for a perk.

    Looks in the perk's GE directory for OngoingTagRequirements -> RequireTags,
    both in the main Properties and in TargetTagRequirementsGameplayEffectComponent entries.

    Returns a deduplicated list of human-readable condition strings.
    """
    perk_dir = PERK_GE_DIR / perk_id
    if not perk_dir.exists():
        return []

    all_tags = set()

    # Try all GE_*.json files in the perk directory
    for ge_file in perk_dir.glob("GE_*.json"):
        data = load_json_silent(ge_file)
        if data is None or not isinstance(data, list):
            continue
        for obj in data:
            props = obj.get("Properties", {})
            # Check direct OngoingTagRequirements in Properties
            otr = props.get("OngoingTagRequirements", {})
            for tag in otr.get("RequireTags", []):
                if tag:
                    all_tags.add(tag)
            # Check TargetTagRequirementsGameplayEffectComponent entries
            if obj.get("Type") == "TargetTagRequirementsGameplayEffectComponent":
                otr2 = props.get("OngoingTagRequirements", {})
                for tag in otr2.get("RequireTags", []):
                    if tag:
                        all_tags.add(tag)

    if not all_tags:
        return []

    conditions = sorted(set(_tag_to_condition(tag) for tag in all_tags))
    return conditions


# ═══════════════════════════════════════════════════════════════════════
# SECTION: Scaling Formulas
# Extracts damage/healing scaling from SpellEffect, SkillEffect, and
# MusicEffect files. Builds formula text and worked examples using the
# class's own base power stats.
# ═══════════════════════════════════════════════════════════════════════

SKILL_EFFECT_DIR_V2 = RAW_V2 / "Skill" / "SkillEffect"


def _extract_scaling_from_effect(effect_path, derived_stats=None):
    """Extract scaling data from a SpellEffect/SkillEffect/MusicEffect file.

    Returns a dict with base_damage, damage_type, scaling_pct, impact_power,
    formula, formula_text, and example, or None if no scaling data found.
    """
    data = load_json_silent(effect_path)
    if data is None:
        return None
    if not isinstance(data, list) or not data:
        return None

    props = data[0].get("Properties", {})

    magical_base = props.get("ExecMagicalDamageBase")
    physical_base = props.get("ExecPhysicalDamageBase")
    magical_heal_base = props.get("ExecMagicalHealBase")
    bonus_ratio = props.get("ExecAttributeBonusRatio")
    impact_power = props.get("ExecImpactPower")

    # Determine if this is a heal effect
    is_heal = magical_heal_base is not None and magical_base is None and physical_base is None

    # Must have at least a damage/heal base or bonus ratio to be meaningful scaling
    if magical_base is None and physical_base is None and magical_heal_base is None and bonus_ratio is None:
        return None

    if is_heal:
        base_damage = magical_heal_base
        damage_type = "magical"
    else:
        base_damage = magical_base if magical_base is not None else physical_base
        damage_type = "magical" if magical_base is not None else "physical"

    scaling_pct = bonus_ratio / 10.0 if bonus_ratio is not None else None

    # Effect label: "healing" for heals, "damage" for everything else
    effect_word = "healing" if is_heal else "damage"

    # Power type label
    is_magical = damage_type == "magical"
    power_label = "Magic" if is_magical else "Physical"

    # Build legacy formula string (backward-compatible)
    parts = []
    if base_damage is not None:
        parts.append(f"{base_damage} base {damage_type} {effect_word}")
    if scaling_pct is not None:
        parts.append(f"{_format_number(scaling_pct)}% Power Scaling")

    result = {}
    if base_damage is not None:
        result["base_damage"] = base_damage
        result["damage_type"] = damage_type
    if is_heal:
        result["is_heal"] = True
    if scaling_pct is not None:
        result["scaling_pct"] = scaling_pct
    if impact_power is not None:
        result["impact_power"] = impact_power
    if parts:
        result["formula"] = " + ".join(parts)

    # Build formula_text and example
    if base_damage is not None and scaling_pct is not None:
        result["formula_text"] = (
            f"Total = {base_damage} + ({_format_number(scaling_pct)}% x {power_label} Power)"
        )
    elif scaling_pct is not None and base_damage is None:
        result["formula_text"] = (
            f"Total = {power_label} Power x {_format_number(scaling_pct)}%"
        )
    elif base_damage is not None and scaling_pct is None:
        result["formula_text"] = (
            f"Flat {base_damage} {damage_type} {effect_word} (no scaling)"
        )

    # Compute worked example using the class's own base stats
    if derived_stats is not None:
        power = derived_stats.get("magic_power", 0) if is_magical else derived_stats.get("physical_power", 0)
        power_val = round(power, 1)
        if base_damage is not None and scaling_pct is not None:
            scaled_rounded = int(round(scaling_pct / 100.0 * power_val))
            total_display = base_damage + scaled_rounded
            result["example"] = (
                f"With {_format_number(power_val)} {power_label} Power: "
                f"{base_damage} + {scaled_rounded} = {total_display} {effect_word}"
            )
        elif scaling_pct is not None and base_damage is None:
            total = int(round(scaling_pct / 100.0 * power_val))
            result["example"] = (
                f"With {_format_number(power_val)} {power_label} Power: "
                f"{total} {effect_word}"
            )
        # No example needed for flat damage (no scaling)

    return result if result else None


def extract_spell_scaling(spell_id, derived_stats=None):
    """Extract scaling formula from SpellEffect files for a spell.

    Tries multiple naming patterns:
      Id_SpellEffect_{spell_id}Hit.json
      Id_SpellEffect_{spell_id}_Hit.json
    """
    candidates = [
        SPELL_EFFECT_DIR / f"Id_SpellEffect_{spell_id}Hit.json",
        SPELL_EFFECT_DIR / f"Id_SpellEffect_{spell_id}_Hit.json",
    ]
    for path in candidates:
        if path.exists():
            result = _extract_scaling_from_effect(path, derived_stats)
            if result is not None:
                return result
    # Try variant names like FlamefrostSpearHit_FireDamage, _IceDamage, etc.
    import glob as _glob
    for variant in sorted(_glob.glob(str(SPELL_EFFECT_DIR / f"Id_SpellEffect_{spell_id}Hit_*.json"))):
        result = _extract_scaling_from_effect(Path(variant), derived_stats)
        if result is not None:
            return result
    return None


def extract_skill_scaling(skill_id, derived_stats=None):
    """Extract scaling formula from SkillEffect files for a skill.

    Tries multiple naming patterns:
      Id_SkillEffect_{skill_id}_Hit.json
      Id_SkillEffect_{skill_id}_HitDamage.json
      Id_SkillEffect_{skill_id}Hit.json
    """
    candidates = [
        SKILL_EFFECT_DIR_V2 / f"Id_SkillEffect_{skill_id}_Hit.json",
        SKILL_EFFECT_DIR_V2 / f"Id_SkillEffect_{skill_id}_HitDamage.json",
        SKILL_EFFECT_DIR_V2 / f"Id_SkillEffect_{skill_id}Hit.json",
    ]
    for path in candidates:
        if path.exists():
            result = _extract_scaling_from_effect(path, derived_stats)
            if result is not None:
                return result
    return None


def extract_song_scaling(song_id, derived_stats=None):
    """Extract scaling formula from MusicEffect files for a Bard song.

    Uses the Perfect tier for the displayed formula:
      Id_MusicEffect_{song_id}_Perfect.json
    """
    path = MUSIC_EFFECT_DIR / f"Id_MusicEffect_{song_id}_Perfect.json"
    if path.exists():
        return _extract_scaling_from_effect(path, derived_stats)
    return None


# ═══════════════════════════════════════════════════════════════════════
# SECTION: Data Collection
# Collects perks, skills, spells, songs, shapeshifts, and spell merge
# recipes for each class. Each collector reads extracted/raw files,
# resolves descriptions, and attaches icons/scaling/conditions.
# ═══════════════════════════════════════════════════════════════════════


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
        # Get description using override-aware lookup
        desc_path = _find_desc_path_perk(short_name)
        description = get_description(short_name, loc, desc_path)
        is_default = perk_id in default_ids
        conditions = extract_perk_conditions(short_name)
        perk_entry = {
            "id": short_name,
            "name": display_name,
            "description": description,
            "is_default": is_default,
        }
        if conditions:
            perk_entry["conditions"] = conditions
        icon_path = _find_icon("perks", short_name)
        if icon_path:
            perk_entry["icon"] = icon_path
        perks.append(perk_entry)
    return perks


def collect_skills(class_name, loc, derived_stats=None):
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
        # Get description using override-aware lookup
        desc_path = _find_desc_path_skill(short_name)
        description = get_description(short_name, loc, desc_path)
        # Extract skill_type last segment (e.g., "Type.Skill.Instant" -> "instant")
        raw_type = data.get("skill_type", "")
        skill_type = raw_type.split(".")[-1].lower() if raw_type else ""
        scaling = extract_skill_scaling(short_name, derived_stats)
        skill_entry = {
            "id": short_name,
            "name": display_name,
            "description": description,
            "skill_type": skill_type,
            "skill_tier": data.get("skill_tier", 1),
            "use_moving": data.get("use_moving", False),
        }
        if scaling is not None:
            skill_entry["scaling"] = scaling
        icon_path = _find_icon("skills", short_name)
        if icon_path:
            skill_entry["icon"] = icon_path
        skills.append(skill_entry)
    return skills


def collect_spells(class_name, loc, derived_stats=None):
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
        # Get description using override-aware lookup
        desc_path = _find_desc_path_spell(short_name)
        description = get_description(short_name, loc, desc_path)
        # Extract source_type last segment
        source_type_tag = props.get("SourceType", {}).get("TagName", "")
        source_type = source_type_tag.split(".")[-1].lower() if source_type_tag else ""
        # Extract cost_type last segment
        cost_type_tag = props.get("CostType", {}).get("TagName", "")
        cost_type = cost_type_tag.split(".")[-1].lower() if cost_type_tag else ""
        # Extract casting_type last segment
        casting_type_tag = props.get("CastingType", {}).get("TagName", "")
        casting_type = casting_type_tag.split(".")[-1].lower() if casting_type_tag else ""
        scaling = extract_spell_scaling(short_name, derived_stats)
        spell_entry = {
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
        }
        if scaling is not None:
            spell_entry["scaling"] = scaling
        icon_path = _find_icon("spells", short_name)
        if icon_path:
            spell_entry["icon"] = icon_path
        spells.append(spell_entry)
    return spells


def _read_song_note_count(short_name):
    """Read note count from PlayMusicData file for a Bard song.

    Returns (note_count, channeling_notes) tuple.
    """
    play_path = MUSIC_PLAY_DIR / f"{short_name}_PlayMusic.json"
    data = load_json_silent(play_path)
    if data is None:
        return None, None
    props = data[0].get("Properties", {}) if isinstance(data, list) and data else {}
    play_datas = props.get("PlayMusicDatas", [])
    note_count = len(play_datas) if play_datas else None
    channeling_datas = props.get("ChannelingPlayMusicDatas", [])
    channeling_notes = len(channeling_datas) if channeling_datas else 0
    return note_count, channeling_notes


def collect_songs(class_name, loc, derived_stats=None):
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
        # Get description using override-aware lookup
        desc_path = _find_desc_path_music(short_name)
        description = get_description(short_name, loc, desc_path)
        # Extract source_type last segment
        source_type_tag = props.get("SourceType", {}).get("TagName", "")
        source_type = source_type_tag.split(".")[-1].lower() if source_type_tag else ""
        # Extract casting_type from PlayType last segment
        play_type_tag = props.get("PlayType", {}).get("TagName", "")
        casting_type = play_type_tag.split(".")[-1].lower() if play_type_tag else ""

        scaling = extract_song_scaling(short_name, derived_stats)
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
        if scaling is not None:
            song_entry["scaling"] = scaling
        icon_path = _find_icon("music", short_name)
        if icon_path:
            song_entry["icon"] = icon_path

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

        # Enhancement 4: Add note count from PlayMusicData
        note_count, channeling_notes = _read_song_note_count(short_name)
        if note_count is not None:
            song_entry["note_count"] = note_count
            song_entry["channeling_notes"] = channeling_notes or 0

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
        icon_path = _find_icon("shapeshifts", short_name)
        if icon_path:
            ss_entry["icon"] = icon_path

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


def collect_spell_merge_recipes(loc, derived_stats=None):
    """Collect spell merge recipes from the SpellMergeGroup data.

    Args:
        loc: Localization dictionary from Game.json.
        derived_stats: Sorcerer derived stats dict for scaling example values.
    """
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
        # Result spell icon
        result_icon = _find_icon("spells", merge_short)
        # Result spell description
        desc_path = _find_desc_path_spell(merge_short)
        result_description = get_description(merge_short, loc, desc_path)
        # Result spell scaling
        result_scaling = extract_spell_scaling(merge_short, derived_stats)
        sources = entry.get("SourceSpells", [])
        source_list = []
        for src in sources:
            src_name_raw = src.get("PrimaryAssetName", "")
            src_short = extract_id_name(src_name_raw, "Id_Spell_")
            src_display = to_display_name(src_short)
            src_loc_key = f"Text_DesignData_Spell_Spell_{src_short}"
            src_display = loc.get(src_loc_key, src_display)
            src_icon = _find_icon("spells", src_short)
            src_entry = {"name": src_display}
            if src_icon:
                src_entry["icon"] = src_icon
            source_list.append(src_entry)
        recipe = {
            "result": merge_display,
            "result_slug": to_slug(merge_display),
            "sources": source_list,
        }
        if result_icon:
            recipe["result_icon"] = result_icon
        if result_description:
            recipe["result_description"] = result_description
        if result_scaling is not None:
            recipe["result_scaling"] = result_scaling
        recipes.append(recipe)
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
    skills = collect_skills(class_name, loc, derived_stats)

    # Spells
    spells = collect_spells(class_name, loc, derived_stats)

    # Songs (Bard music) - merge into spells list
    songs = collect_songs(class_name, loc, derived_stats)
    if songs:
        spells.extend(songs)

    # Shapeshifts
    shapeshifts = collect_shapeshifts(class_name, loc)

    # Usable item count
    usable_item_count = get_usable_item_count(class_name)

    # Class icon
    class_icon = _find_icon("classes", class_name)

    result = {
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
    if class_icon:
        result["icon"] = class_icon
    return result


# ═══════════════════════════════════════════════════════════════════════
# SECTION: Icon Management
# Copies icon PNGs from FModel export directory to website/public/icons/
# and resolves icon web paths for each ability type. Handles overrides
# for non-standard icon filenames via ICON_OVERRIDES.
# ═══════════════════════════════════════════════════════════════════════


def copy_icons():
    """Copy icon PNGs from export directory to website/public/icons/."""
    icon_mappings = {
        "classes": "IconClass",
        "perks": "IconPerk",
        "skills": "IconSkill",
        "spells": "IconSpell",
        "music": "IconMusic",
        "shapeshifts": "IconShapeShift",
    }

    total = 0
    for dest_subdir, src_subdir in icon_mappings.items():
        src_dir = ICONS_SRC / src_subdir
        dst_dir = ICONS_DST / dest_subdir
        if not src_dir.exists():
            print(f"  WARNING: Icon source not found: {src_dir}")
            continue
        dst_dir.mkdir(parents=True, exist_ok=True)
        for png in src_dir.glob("*.png"):
            # For class icons, only copy the large variants (ClassIcon_L_*)
            # Skip Small (S) and extra-large (XL) variants
            if dest_subdir == "classes":
                if not png.name.startswith("ClassIcon_L_"):
                    continue
            dst_path = dst_dir / png.name
            if not dst_path.exists() or png.stat().st_mtime > dst_path.stat().st_mtime:
                shutil.copy2(png, dst_path)
            total += 1
    print(f"  Synced {total} icon files to {ICONS_DST}")


def _find_icon(subdir, pattern_name):
    """Check if an icon file exists and return its web path, or None."""
    # Check ICON_OVERRIDES first for non-standard icon filenames
    override_key = (subdir, pattern_name)
    if override_key in ICON_OVERRIDES:
        override_fname = ICON_OVERRIDES[override_key]
        if (ICONS_DST / subdir / override_fname).exists():
            return f"/icons/{subdir}/{override_fname}"

    # Build candidate filenames based on subdirectory
    candidates = []
    if subdir == "perks":
        candidates.append(f"Icon_Perk_{pattern_name}.png")
    elif subdir == "skills":
        candidates.append(f"Icon_Skill_{pattern_name}.png")
    elif subdir == "spells":
        candidates.append(f"Icon_Spell_{pattern_name}.png")
    elif subdir == "music":
        candidates.append(f"Icon_Music_{pattern_name}.png")
    elif subdir == "shapeshifts":
        candidates.append(f"Icon_ShapeShift_{pattern_name}.png")
    elif subdir == "classes":
        candidates.append(f"ClassIcon_L_{pattern_name}.png")

    for fname in candidates:
        if (ICONS_DST / subdir / fname).exists():
            return f"/icons/{subdir}/{fname}"
    return None


# ═══════════════════════════════════════════════════════════════════════
# SECTION: Main Entry Point
# Orchestrates the full build: copies icons, loads localization, builds
# all 10 classes, collects spell merge recipes, writes classes.json.
# ═══════════════════════════════════════════════════════════════════════


def main():
    print("Building classes.json...")
    now = datetime.now(timezone.utc)

    # Copy icons from export directory
    if ICONS_SRC.exists():
        copy_icons()
    else:
        print(f"  WARNING: Icon source directory not found: {ICONS_SRC}")

    # Load localization
    loc = load_localization()
    print(f"  Loaded {len(loc)} localization keys")

    # Build each class
    classes = []
    for class_name in CLASS_NAMES:
        class_data = build_class(class_name, loc)
        if class_data is not None:
            classes.append(class_data)

    # Spell merge recipes — use Sorcerer derived stats for scaling examples
    sorcerer_derived = None
    for c in classes:
        if c["name"] == "Sorcerer":
            sorcerer_derived = c["derived_stats"]
            break
    spell_merge_recipes = collect_spell_merge_recipes(loc, sorcerer_derived)
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
