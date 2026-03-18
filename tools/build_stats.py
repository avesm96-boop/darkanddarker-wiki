"""
build_stats.py - Compile all stat/attribute data into website/public/data/stats.json

GAME UPDATE WORKFLOW:
  1. Re-export from FModel (see docs/pipeline/game-update-workflow.md)
  2. Run: py -3 -m pipeline.extract_all --force
  3. Run: py -3 tools/build_stats.py

Reads from:
  - extracted/engine/curves.json                                    (all curve tables)
  - extracted/engine/constants.json                                 (game constants / caps)
  - extracted/classes/Id_PlayerCharacterEffect_[Class].json         (base stats per class)
"""

# ═══════════════════════════════════════════════════════════════════════
# SECTION: Imports & Constants
# ═══════════════════════════════════════════════════════════════════════

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED_ENGINE = ROOT / "extracted" / "engine"
EXTRACTED_CLASSES = ROOT / "extracted" / "classes"
OUTPUT_FILE = ROOT / "website" / "public" / "data" / "stats.json"

# Class order for display
CLASS_ORDER = [
    "Barbarian", "Bard", "Cleric", "Druid", "Fighter",
    "Ranger", "Rogue", "Sorcerer", "Warlock", "Wizard",
]

# File ID → display name mapping
CLASS_FILE_MAP = {
    "Id_PlayerCharacterEffect_Barbarian": "Barbarian",
    "Id_PlayerCharacterEffect_Bard": "Bard",
    "Id_PlayerCharacterEffect_Cleric": "Cleric",
    "Id_PlayerCharacterEffect_Druid": "Druid",
    "Id_PlayerCharacterEffect_Fighter": "Fighter",
    "Id_PlayerCharacterEffect_Ranger": "Ranger",
    "Id_PlayerCharacterEffect_Rogue": "Rogue",
    "Id_PlayerCharacterEffect_Sorcerer": "Sorcerer",
    "Id_PlayerCharacterEffect_Warlock": "Warlock",
    "Id_PlayerCharacterEffect_Wizard": "Wizard",
}

# ═══════════════════════════════════════════════════════════════════════
# SECTION: Attribute Definitions
# Metadata for each primary attribute — what derived stats it governs,
# descriptions, and which curve tables to reference.
# ═══════════════════════════════════════════════════════════════════════

ATTRIBUTE_DEFS = [
    {
        "id": "strength",
        "name": "Strength",
        "description": "Governs Physical Power, which determines the damage bonus for physical attacks.",
        "icon": "strength",
        "derived_stats": [
            {
                "id": "physical_power",
                "name": "Physical Power",
                "description": "Raw physical power rating. Maps 1:1 from Strength.",
                "mechanic": "Your Physical Power equals your Strength, point for point. This rating is then converted to a damage bonus % via the Physical Power Bonus curve below.",
                "curve_table": "CT_Strength",
                "curve_row": "PhysicalPower",
                "unit": "flat",
            },
            {
                "id": "physical_power_bonus",
                "name": "Physical Power Bonus",
                "description": "Percentage modifier applied to physical damage. Derived from Physical Power rating via a scaling curve.",
                "mechanic": "Your weapon's base damage is multiplied by (1 + this bonus). For example, a Barbarian with 20 STR gets Physical Power 20, which gives roughly +5% bonus. A weapon dealing 30 base damage would deal 30 × 1.05 = 31.5. Below 15 STR the bonus goes negative, reducing your damage.",
                "curve_table": "CT_PhysicalPower",
                "curve_row": "PhysicalDamageMod",
                "unit": "percent",
            },
        ],
    },
    {
        "id": "vigor",
        "name": "Vigor",
        "description": "Determines base maximum health and health recovery rate. Higher Vigor means a larger health pool and faster natural regeneration.",
        "icon": "vigor",
        "derived_stats": [
            {
                "id": "max_health_base",
                "name": "Max Health",
                "description": "Base maximum health points. Scales with Vigor via a nonlinear curve.",
                "mechanic": "This is your health pool before any gear bonuses. The curve has diminishing returns — early points of Vigor give more HP than later ones. A Fighter with 15 VIG gets 115 HP, while a Barbarian with 25 VIG gets 131.5 HP — only 16.5 more HP for 10 extra points.",
                "curve_table": "CT_MaxHealthBase",
                "curve_row": "MaxHealthBase",
                "unit": "flat",
            },
            {
                "id": "health_recovery_mod",
                "name": "Health Recovery",
                "description": "Modifier to health regeneration rate while resting.",
                "mechanic": "When you sit down to rest, your HP regenerates each tick. This modifier changes how fast: HP per tick = Base Recovery × (1 + this value). At +70% (Barbarian, 25 VIG), you heal 1.7× as fast. Below 15 VIG, recovery becomes slower — a Rogue with 6 VIG has -27%, making resting almost twice as slow.",
                "curve_table": "CT_RecoveryMod",
                "curve_row": "HealthRecoveryMod",
                "unit": "percent",
            },
        ],
    },
    {
        "id": "agility",
        "name": "Agility",
        "description": "Affects movement speed and action speed. Higher Agility increases move speed (with diminishing returns) and weapon swing/attack speed.",
        "icon": "agility",
        "derived_stats": [
            {
                "id": "move_speed_base",
                "name": "Move Speed Bonus",
                "description": "Flat bonus added to your base movement speed.",
                "mechanic": "Your total Move Speed = Base (300) + this bonus, but hard capped at 330. A Rogue with 25 AGI gets +5 bonus = 305 move speed. A Ranger with 20 AGI gets +2.5 = 302.5. Gear can push you further toward the 330 cap. Below 15 AGI you get a penalty — at 0 AGI you'd lose 10 move speed.",
                "curve_table": "CT_Agility",
                "curve_row": "MoveSpeedBase",
                "unit": "flat",
            },
            {
                "id": "action_speed_agi",
                "name": "Action Speed (from Agility)",
                "description": "Action speed modifier from Agility. Contributes to your total Action Speed alongside Dexterity.",
                "mechanic": "Action Speed controls how fast you swing weapons, draw bows, and block. Both Agility and Dexterity contribute, but Dexterity has 3× more weight. Verified from the game binary: the formula is exactly 0.25 × Agility + 0.75 × Dexterity, which is then fed into the curve shown below. For example, a Rogue (25 AGI, 20 DEX) uses input 0.25×25 + 0.75×20 = 21.25, giving +7.8% Action Speed.",
                "curve_table": "CT_Agility",
                "curve_row": "ActionSpeed",
                "unit": "percent",
            },
        ],
    },
    {
        "id": "dexterity",
        "name": "Dexterity",
        "description": "Affects action speed, manual dexterity (instrument playing for Bard), and item equip speed for weapons and armor.",
        "icon": "dexterity",
        "derived_stats": [
            {
                "id": "action_speed_dex",
                "name": "Action Speed (from Dexterity)",
                "description": "Action speed modifier from Dexterity. The dominant contributor to total Action Speed.",
                "mechanic": "Dexterity is the primary Action Speed stat — verified from the game binary: the formula is 0.25 × Agility + 0.75 × Dexterity. Each point of Dexterity gives 3× more Action Speed than a point of Agility. The weighted sum is the input to this curve. Prioritize Dexterity when optimizing attack speed.",
                "curve_table": "CT_ActionSpeed",
                "curve_row": "ActionSpeed",
                "unit": "percent",
            },
            {
                "id": "manual_dexterity",
                "name": "Manual Dexterity",
                "description": "Affects Bard instrument playing speed.",
                "mechanic": "Bard-specific stat that controls how quickly you can play instruments. Scales well up to about 45 DEX, then heavily plateaus — going from 45 to 100 DEX barely improves it. Most classes won't notice this stat.",
                "curve_table": "CT_Dexterity",
                "curve_row": "ManualDexterity",
                "unit": "percent",
            },
            {
                "id": "item_equip_speed",
                "name": "Item Equip Speed",
                "description": "Speed modifier for equipping armor and ranged weapons.",
                "mechanic": "Controls how long it takes to put on armor pieces and equip ranged weapons during a match. At very low DEX (0-1), equipping is nearly frozen (-95%). At 15 DEX it's normal speed. Higher DEX dramatically speeds it up — at 35 DEX you equip at 2× normal speed. This matters most for classes that swap gear mid-fight.",
                "curve_table": "CT_Dexterity",
                "curve_row": "ItemEquipSpeed",
                "unit": "percent",
            },
        ],
    },
    {
        "id": "will",
        "name": "Will",
        "description": "The primary stat for magic users. Governs Magical Power, Magic Resistance, buff/debuff durations, and magical interaction speed (shrines, portals).",
        "icon": "will",
        "derived_stats": [
            {
                "id": "magical_power",
                "name": "Magical Power",
                "description": "Raw magical power rating. Maps 1:1 from Will.",
                "mechanic": "Works exactly like Physical Power but for spells. Your Magical Power equals your Will stat point for point. This rating then converts to a damage bonus % via the Magical Power Bonus curve.",
                "curve_table": "CT_Will",
                "curve_row": "MagicalPower",
                "unit": "flat",
            },
            {
                "id": "magical_power_bonus",
                "name": "Magical Power Bonus",
                "description": "Percentage modifier applied to magical/spell damage.",
                "mechanic": "Spell damage is multiplied by (1 + this bonus). Uses the same curve shape as Physical Power Bonus. A Sorcerer with 25 WIL gets +10% spell damage, while a Rogue with 10 WIL takes a -8% penalty to any magical damage they deal.",
                "curve_table": "CT_MagicalPower",
                "curve_row": "MagicalDamageMod",
                "unit": "percent",
            },
            {
                "id": "magic_resistance",
                "name": "Magic Resistance",
                "description": "Magic resistance rating that reduces incoming spell damage.",
                "mechanic": "This rating feeds into the Magical Damage Reduction curve (see Defense tab). Higher Will gives higher resistance, which means less spell damage taken. A Sorcerer with 25 WIL gets 54 Magic Resistance. This is separate from Armor Rating — you can be well-protected against spells but vulnerable to weapons, or vice versa.",
                "curve_table": "CT_Will",
                "curve_row": "MagicResistance",
                "unit": "flat",
            },
            {
                "id": "buff_duration_mod",
                "name": "Buff Duration",
                "description": "Modifier to how long beneficial effects (buffs) last on you.",
                "mechanic": "Buff duration = Base Duration × (1 + this modifier). A Cleric with 23 WIL gets about +9.6% — their Protection spell lasts ~10% longer. Uses the same curve shape as Physical Power Bonus. Below 15 WIL, your buffs expire faster.",
                "curve_table": "CT_Will",
                "curve_row": "BuffDurationMod",
                "unit": "percent",
            },
            {
                "id": "debuff_duration_mod",
                "name": "Debuff Duration",
                "description": "Modifier to how long negative effects (debuffs) last on you.",
                "mechanic": "This curve is inverted — positive values mean debuffs last LONGER. At low Will, debuffs are devastating: a Rogue with 10 WIL has +12.4%, meaning poison/slow effects last ~12% longer. At high Will, debuffs are shortened. The penalty is extreme at 0 Will — debuffs would last 5× normal duration.",
                "curve_table": "CT_Will",
                "curve_row": "DebuffDurationMod",
                "unit": "percent",
                "inverted": True,
            },
            {
                "id": "magical_interaction_speed",
                "name": "Magical Interaction Speed",
                "description": "Speed modifier for magical interactions like opening shrines and portals.",
                "mechanic": "Controls how quickly you can activate shrines, open portals, and interact with magical objects. Uses the same curve as Health Recovery. A Wizard with 20 WIL opens shrines about 35% faster than baseline.",
                "curve_table": "CT_Will",
                "curve_row": "MagicalInteractionSpeed",
                "unit": "percent",
            },
        ],
    },
    {
        "id": "knowledge",
        "name": "Knowledge",
        "description": "Governs spell casting speed, memory capacity (how many spells can be equipped), and memory recovery rate (spell recharge speed).",
        "icon": "knowledge",
        "derived_stats": [
            {
                "id": "spell_casting_speed",
                "name": "Spell Casting Speed",
                "description": "Modifier to how fast you cast spells.",
                "mechanic": "Cast time = Base Cast Time / (1 + this modifier). A Wizard with 25 KNO gets +21% — a spell with 2s base cast time takes 2 / 1.21 = 1.65s. This is critical for spell classes. Barbarian at 5 KNO gets -35%, making their rare spell casts painfully slow.",
                "curve_table": "CT_Knowledge",
                "curve_row": "SpellCastingSpeed",
                "unit": "percent",
            },
            {
                "id": "memory_capacity",
                "name": "Memory Capacity",
                "description": "Determines how many spell slots are available.",
                "mechanic": "Each spell has a memory cost. Your Memory Capacity limits which spells you can equip. Below 7 Knowledge you get zero capacity and cannot equip any spells. Above that, each point gives roughly 1 more capacity. A Wizard with 25 KNO gets 19 capacity, enough for several spells.",
                "curve_table": "CT_Knowledge",
                "curve_row": "MemoryCapacity",
                "unit": "flat",
            },
            {
                "id": "memory_recovery_mod",
                "name": "Memory Recovery",
                "description": "Multiplier for how fast spent spell slots recharge.",
                "mechanic": "When you rest at a campfire or meditate, your spent spell slots recover. This multiplier speeds that up. Unlike Health Recovery, this never goes negative — even at 0 Knowledge you still recover at 0.43× rate. At 25 KNO you get about 0.85× rate, and it climbs steeply above 30.",
                "curve_table": "CT_RecoveryMod",
                "curve_row": "MemoryRecoveryMod",
                "unit": "multiplier",
            },
        ],
    },
    {
        "id": "resourcefulness",
        "name": "Resourcefulness",
        "description": "Governs regular interaction speed (opening chests, doors), cooldown reduction for skills/spells, and persuasiveness (Bard buff/debuff modifier).",
        "icon": "resourcefulness",
        "derived_stats": [
            {
                "id": "regular_interaction_speed",
                "name": "Regular Interaction Speed",
                "description": "Speed modifier for non-magical interactions like opening chests, doors, and reviving.",
                "mechanic": "Controls how fast you open chests, unlock doors, disarm traps, and revive teammates. A Rogue with 25 RES gets +52% — they open chests roughly 1.5× faster than a Fighter. Combined with Dexterity's contribution, Rogues are the fastest looters.",
                "curve_table": "CT_RegularInteractionSpeedBase",
                "curve_row": "RegularInteractionSpeed",
                "unit": "percent",
            },
            {
                "id": "cooldown_reduction",
                "name": "Cooldown Reduction",
                "description": "Reduces the cooldown time on your skills and spells.",
                "mechanic": "Effective Cooldown = Base Cooldown × (1 - this value). A Rogue with 25 RES gets about +20% CDR — a 30s cooldown becomes 30 × 0.8 = 24s. This is hard capped at 65% reduction, so cooldowns can never be reduced below 35% of their base value.",
                "curve_table": "CT_Resourcefulness",
                "curve_row": "CooldownReduction",
                "unit": "percent",
            },
            {
                "id": "persuasiveness",
                "name": "Persuasiveness",
                "description": "Affects Bard buff/debuff effectiveness.",
                "mechanic": "Bard-only stat. Increases the potency of your songs' buff and debuff effects on allies and enemies. Scales linearly up to about 35 RES, then hits diminishing returns and eventually plateaus. Most non-Bard classes can ignore this stat.",
                "curve_table": "CT_Resourcefulness",
                "curve_row": "Persuasiveness",
                "unit": "flat",
            },
        ],
    },
]


# ═══════════════════════════════════════════════════════════════════════
# SECTION: Curve Helpers
# ═══════════════════════════════════════════════════════════════════════

def interpolate_curve(keys: list[dict], x: float) -> float:
    """Linear interpolation on a curve's key array."""
    if not keys:
        return 0.0
    if x <= keys[0]["time"]:
        return keys[0]["value"]
    if x >= keys[-1]["time"]:
        return keys[-1]["value"]
    for i in range(len(keys) - 1):
        t0, v0 = keys[i]["time"], keys[i]["value"]
        t1, v1 = keys[i + 1]["time"], keys[i + 1]["value"]
        if t0 <= x <= t1:
            if t1 == t0:
                return v0
            frac = (x - t0) / (t1 - t0)
            return v0 + frac * (v1 - v0)
    return keys[-1]["value"]


def simplify_curve_keys(keys: list[dict]) -> list[dict]:
    """Return curve keys simplified for frontend (remove redundant mid-points
    on perfectly linear segments, but keep all inflection points)."""
    if len(keys) <= 3:
        return keys
    result = [keys[0]]
    for i in range(1, len(keys) - 1):
        prev = keys[i - 1]
        curr = keys[i]
        nxt = keys[i + 1]
        # Check if curr lies exactly on the line from prev to nxt
        dt_total = nxt["time"] - prev["time"]
        if dt_total == 0:
            result.append(curr)
            continue
        expected = prev["value"] + (curr["time"] - prev["time"]) / dt_total * (nxt["value"] - prev["value"])
        if abs(curr["value"] - expected) > 0.0001:
            result.append(curr)
    result.append(keys[-1])
    return result


def get_curve_keys(curves: dict, table_name: str, row_name: str) -> list[dict]:
    """Extract and return the key points from a curve table row."""
    table = curves.get("curve_tables", {}).get(table_name, {})
    row = table.get("rows", {}).get(row_name, {})
    return row.get("keys", [])


# ═══════════════════════════════════════════════════════════════════════
# SECTION: Load Source Data
# ═══════════════════════════════════════════════════════════════════════

def load_curves() -> dict:
    path = EXTRACTED_ENGINE / "curves.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_constants() -> dict:
    path = EXTRACTED_ENGINE / "constants.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("constants", data)


def load_class_base_stats() -> list[dict]:
    """Load base stats for each class from extracted files."""
    classes = []
    for file_id, class_name in CLASS_FILE_MAP.items():
        path = EXTRACTED_CLASSES / f"{file_id}.json"
        if not path.exists():
            print(f"  [WARN] Missing class file: {path}")
            continue
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        # Extract base stats — flat fields like strength_base, vigor_base, etc.
        attr_keys = [
            "strength", "vigor", "agility", "dexterity",
            "will", "knowledge", "resourcefulness",
        ]
        stats = {}
        for key in attr_keys:
            val = data.get(f"{key}_base", 0)
            stats[key] = int(val)
        move_speed = int(data.get("move_speed_base", 300))

        classes.append({
            "id": class_name.lower(),
            "name": class_name,
            "base_stats": stats,
            "move_speed": move_speed,
        })

    # Sort by CLASS_ORDER
    order_map = {name.lower(): i for i, name in enumerate(CLASS_ORDER)}
    classes.sort(key=lambda c: order_map.get(c["id"], 99))
    return classes


# ═══════════════════════════════════════════════════════════════════════
# SECTION: Build Output Data
# ═══════════════════════════════════════════════════════════════════════

def build_attributes(curves: dict, classes: list[dict]) -> list[dict]:
    """Build the attributes array with curve data and per-class values."""
    attributes = []
    for attr_def in ATTRIBUTE_DEFS:
        attr = {
            "id": attr_def["id"],
            "name": attr_def["name"],
            "description": attr_def["description"],
            "icon": attr_def["icon"],
            "derived_stats": [],
            "class_base_values": {},
        }

        # Per-class base values for this attribute
        for cls in classes:
            val = cls["base_stats"].get(attr_def["id"], 0)
            attr["class_base_values"][cls["id"]] = val

        # Derived stats with curves
        for ds_def in attr_def["derived_stats"]:
            raw_keys = get_curve_keys(curves, ds_def["curve_table"], ds_def["curve_row"])
            simplified = simplify_curve_keys(raw_keys)

            ds = {
                "id": ds_def["id"],
                "name": ds_def["name"],
                "description": ds_def["description"],
                "unit": ds_def["unit"],
                "curve": [{"x": k["time"], "y": k["value"]} for k in simplified],
                "curve_full": [{"x": k["time"], "y": k["value"]} for k in raw_keys],
                "range": {
                    "input_min": raw_keys[0]["time"] if raw_keys else 0,
                    "input_max": raw_keys[-1]["time"] if raw_keys else 100,
                    "output_min": min(k["value"] for k in raw_keys) if raw_keys else 0,
                    "output_max": max(k["value"] for k in raw_keys) if raw_keys else 0,
                },
                "baseline": interpolate_curve(raw_keys, 15),
            }
            if ds_def.get("mechanic"):
                ds["mechanic"] = ds_def["mechanic"]
            if ds_def.get("inverted"):
                ds["inverted"] = True
            attr["derived_stats"].append(ds)

        attributes.append(attr)
    return attributes


def build_defense_curves(curves: dict) -> dict:
    """Build armor rating and magic resistance defense curves."""
    ar_keys = get_curve_keys(curves, "CT_ArmorRating", "PhysicalReduction")
    mr_keys = get_curve_keys(curves, "CT_MagicResistance", "MagicalReduction")

    return {
        "armor_rating": {
            "name": "Physical Damage Reduction",
            "description": "Converts Armor Rating into percentage physical damage reduction. Subject to heavy diminishing returns at high values.",
            "input_label": "Armor Rating",
            "output_label": "Damage Reduction",
            "unit": "percent",
            "curve": [{"x": k["time"], "y": k["value"]} for k in simplify_curve_keys(ar_keys)],
            "curve_full": [{"x": k["time"], "y": k["value"]} for k in ar_keys],
            "range": {
                "input_min": ar_keys[0]["time"] if ar_keys else 0,
                "input_max": ar_keys[-1]["time"] if ar_keys else 600,
                "output_min": min(k["value"] for k in ar_keys) if ar_keys else 0,
                "output_max": max(k["value"] for k in ar_keys) if ar_keys else 0,
            },
        },
        "magic_resistance": {
            "name": "Magical Damage Reduction",
            "description": "Converts Magic Resistance rating into percentage magical damage reduction. Same diminishing-returns curve shape as physical.",
            "input_label": "Magic Resistance",
            "output_label": "Damage Reduction",
            "unit": "percent",
            "curve": [{"x": k["time"], "y": k["value"]} for k in simplify_curve_keys(mr_keys)],
            "curve_full": [{"x": k["time"], "y": k["value"]} for k in mr_keys],
            "range": {
                "input_min": mr_keys[0]["time"] if mr_keys else 0,
                "input_max": mr_keys[-1]["time"] if mr_keys else 500,
                "output_min": min(k["value"] for k in mr_keys) if mr_keys else 0,
                "output_max": max(k["value"] for k in mr_keys) if mr_keys else 0,
            },
        },
    }


def build_luck_grades(curves: dict) -> dict:
    """Build the luck grade drop weight table."""
    luck_table = curves.get("curve_tables", {}).get("CT_LuckGrade", {})
    grades = {}
    for row_name, row_data in sorted(luck_table.get("rows", {}).items()):
        keys = row_data.get("keys", [])
        grades[row_name] = {
            "curve": [{"x": k["time"], "y": k["value"]} for k in keys],
            "at_zero": keys[0]["value"] if keys else 1.0,
            "at_max": keys[-1]["value"] if keys else 1.0,
        }
    return {
        "description": "Luck modifies drop rate weights per rarity tier. Lower grades (common) decrease with Luck, higher grades (rare/legendary) increase.",
        "grades": grades,
    }


def build_other_curves(curves: dict) -> dict:
    """Build miscellaneous curves (oxygen, rigidity, primitive calc)."""
    result = {}

    # Max Oxygen
    ox_keys = get_curve_keys(curves, "CT_MaxOxygenBase", "MaxOxygenBase")
    result["max_oxygen"] = {
        "name": "Max Oxygen",
        "description": "Maximum breath duration underwater. Scales linearly with the stat.",
        "curve": [{"x": k["time"], "y": k["value"]} for k in ox_keys],
        "range": {
            "input_min": ox_keys[0]["time"] if ox_keys else 0,
            "input_max": ox_keys[-1]["time"] if ox_keys else 100,
            "output_min": min(k["value"] for k in ox_keys) if ox_keys else 100,
            "output_max": max(k["value"] for k in ox_keys) if ox_keys else 150,
        },
    }

    # Rigidity / Coldness
    rig_keys = get_curve_keys(curves, "CT_Rigidity", "Coldness")
    result["rigidity"] = {
        "name": "Freeze Threshold",
        "description": "Maps freeze buildup (0-1) to freeze intensity. Has a sharp ramp that creates a 'freeze threshold' behavior.",
        "curve": [{"x": k["time"], "y": k["value"]} for k in rig_keys],
    }

    # Primitive Calc (true damage)
    pc_keys = get_curve_keys(curves, "CT_PrimitiveCalc", "PrimitiveCalcValue")
    result["primitive_calc"] = {
        "name": "True Damage Scaling",
        "description": "Used for true damage calculations. Shows extreme diminishing returns above 50.",
        "curve": [{"x": k["time"], "y": k["value"]} for k in simplify_curve_keys(pc_keys)],
        "range": {
            "input_min": pc_keys[0]["time"] if pc_keys else 0,
            "input_max": pc_keys[-1]["time"] if pc_keys else 100,
            "output_min": min(k["value"] for k in pc_keys) if pc_keys else 0,
            "output_max": max(k["value"] for k in pc_keys) if pc_keys else 0,
        },
    }

    return result


def build_constants(raw_constants: dict) -> dict:
    """Extract and categorize game constants relevant to stats."""
    prefix = "Id_Constant_"

    def get(key: str, default=None):
        return raw_constants.get(f"{prefix}{key}", default)

    return {
        "caps": {
            "max_cooldown_reduction": get("Attribute_MaxCooldownReductionMod", 0.65),
            "max_physical_damage_reduction": get("Attribute_MaxPhysicalDamageReduction", 0.65),
            "max_physical_damage_reduction_defense_mastery": get("Attribute_MaxPhysicalDamageReduction_DefenseMastery", 0.75),
            "max_magical_damage_reduction": get("Attribute_MaxMagicalDamageReduction", 0.65),
            "max_magical_damage_reduction_iron_will": get("Attribute_MaxMagicalDamageReduction_IronWill", 0.75),
            "max_headshot_damage_mod": get("Attribute_MaxHeadshotDamageMod", 2.0),
            "max_projectile_reduction": get("Attribute_MaxProjectileReductionMod", 0.95),
            "max_spell_casting_speed": get("Attribute_MaxSpellCastingSpeed", 2.0),
            "min_spell_casting_speed": get("Attribute_MinSpellCastingSpeed", -0.95),
            "min_physical_damage_reduction": get("Attribute_MinPhysicalDamageReduction", -6.95),
            "min_magical_damage_reduction": get("Attribute_MinMagicalDamageReduction", -6.95),
            "min_debuff_duration_mod": get("Attribute_MinDebuffDurationMod", -0.95),
            "min_duration_multiplier": get("Attribute_MinDurationMultiplier", 0.05),
            "max_demon_reduction": get("Attribute_MaxDemonReductionMod", 0.65),
            "max_undead_reduction": get("Attribute_MaxUndeadReductionMod", 0.65),
        },
        "movement": {
            "base_move_speed": get("CharacterBaseMoveSpeed", 300.0),
            "max_move_speed": get("CharacterMaxMoveSpeed", 330.0),
            "stop_threshold": get("CharacterStopMovementThreshold", 10.0),
        },
        "hitbox": {
            "head": get("Hitbox_Head", 150.0),
            "head_melee": get("Hitbox_Head_Melee", 150.0),
            "body": get("Hitbox_Body", 100.0),
            "arm": get("Hitbox_Arm", 80.0),
            "hand": get("Hitbox_Hand", 70.0),
            "leg": get("Hitbox_Leg", 60.0),
            "foot": get("Hitbox_Foot", 50.0),
            "defending": get("HitboxState_Defending", 0.5),
        },
        "health": {
            "recoverable_health_ratio": get("RecoverableHealthRatio", 0.65),
            "max_overheal_ratio": get("MaxOverhealedHealthRatio", 0.2),
            "damage_to_oxygen_ratio": get("Attribute_DamageToOxygenRatio", 0.2),
        },
        "spell_recharge": {
            "default_amount": get("SpellRechargeDefaultAmount", 17),
            "meditation_amount": get("SpellRechargeMeditationAmount", 34),
            "campfire_amount": get("SpellRechargeInCampfireAmount", 34),
            "clarity_potion_amount": get("SpellRechargeClarityPotionAmount", 34),
            "chorale_of_clarity_amount": get("SpellRechargeChoraleOfClarityAmount", 8),
            "required_per_tier": get("SpellRequiredRechargeAmountPerTier", 100),
            "cooldown_reduce_rest": get("SpellCooldownReduceRestAmount", 1.0),
            "cooldown_reduce_meditation": get("SpellCooldownReduceMeditationAmount", 1.0),
            "cooldown_reduce_campfire": get("SpellCooldownReduceRestInCampfireAmount", 2.0),
            "skill_cooldown_reduce_rest": get("SkillCooldownReduceRestAmount", 1.0),
            "skill_cooldown_reduce_meditation": get("SkillCooldownReduceMeditationAmount", 1.0),
            "skill_cooldown_reduce_campfire": get("SkillCooldownReduceRestInCampfireAmount", 2.0),
            "campfire_interval": get("CampfireRestSpellSkillRechargeInterval", 1.0),
            "normal_rest_interval": get("NormalRestSpellSkillRechargeInterval", 2.0),
        },
        "water": {
            "magical_projectile_gravity_ratio": get("Water_MagicalProjectileGravityRatio", 1.0),
            "magical_projectile_velocity_ratio": get("Water_MagicalProjectileVelocityRatio", 0.4),
            "projectile_gravity_ratio": get("Water_ProjectileGravityRatio", 0.33),
            "projectile_velocity_ratio": get("Water_ProjectileVelocityRatio", 0.17),
            "spell_aim_range_ratio": get("Water_SpellAimRangeRatio", 0.6),
        },
    }


# ═══════════════════════════════════════════════════════════════════════
# SECTION: Main
# ═══════════════════════════════════════════════════════════════════════

def main():
    print("[build_stats] Loading source data...")
    curves = load_curves()
    raw_constants = load_constants()
    classes = load_class_base_stats()

    print(f"  Loaded {len(curves.get('curve_tables', {}))} curve tables")
    print(f"  Loaded {len(raw_constants)} constants")
    print(f"  Loaded {len(classes)} classes")

    print("[build_stats] Building stats data...")
    attributes = build_attributes(curves, classes)
    defense_curves = build_defense_curves(curves)
    luck_grades = build_luck_grades(curves)
    other_curves = build_other_curves(curves)
    constants = build_constants(raw_constants)

    output = {
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data": {
            "attributes": attributes,
            "defense_curves": defense_curves,
            "luck_grades": luck_grades,
            "other_curves": other_curves,
            "constants": constants,
            "classes": [
                {
                    "id": c["id"],
                    "name": c["name"],
                    "base_stats": c["base_stats"],
                    "move_speed": c["move_speed"],
                }
                for c in classes
            ],
        },
    }

    # Count total derived stat curves
    total_curves = sum(len(a["derived_stats"]) for a in attributes)
    print(f"  {len(attributes)} attributes with {total_curves} derived stat curves")
    print(f"  {len(defense_curves)} defense curves")
    print(f"  {len(luck_grades.get('grades', {}))} luck grades")
    print(f"  {len(other_curves)} other curves")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    size_kb = OUTPUT_FILE.stat().st_size / 1024
    print(f"[build_stats] Written {OUTPUT_FILE} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
