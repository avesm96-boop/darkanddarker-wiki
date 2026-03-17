// Stats with ValueRatio=0.001 — displayed as percentages
// Raw value × 0.001 × 100 = display percentage
// e.g., raw 62 → 6.2%, raw 250 → 25%
const PERCENT_STATS = new Set([
  "Id_ItemPropertyType_Effect_ActionSpeed",
  "Id_ItemPropertyType_Effect_ArmorPenetration",
  "Id_ItemPropertyType_Effect_BuffDurationBonus",
  "Id_ItemPropertyType_Effect_CooldownReductionBonus",
  "Id_ItemPropertyType_Effect_DebuffDurationBonus",
  "Id_ItemPropertyType_Effect_DemonDamageMod",
  "Id_ItemPropertyType_Effect_DemonReductionMod",
  "Id_ItemPropertyType_Effect_HeadshotDamageMod",
  "Id_ItemPropertyType_Effect_HealBonus",
  "Id_ItemPropertyType_Effect_Luck",
  "Id_ItemPropertyType_Effect_MagicalDamageBonus",
  "Id_ItemPropertyType_Effect_MagicalDamageReduction",
  "Id_ItemPropertyType_Effect_MagicalHealing",
  "Id_ItemPropertyType_Effect_MagicalWeaponDamage",
  "Id_ItemPropertyType_Effect_MemoryCapacityBonus",
  "Id_ItemPropertyType_Effect_MoveSpeedBonus",
  "Id_ItemPropertyType_Effect_PhysicalDamageBonus",
  "Id_ItemPropertyType_Effect_PhysicalDamageReduction",
  "Id_ItemPropertyType_Effect_PhysicalHealing",
  "Id_ItemPropertyType_Effect_PhysicalWeaponDamage",
  "Id_ItemPropertyType_Effect_ProjectileReductionMod",
  "Id_ItemPropertyType_Effect_RegularInteractionSpeed",
  "Id_ItemPropertyType_Effect_SpellCastingSpeed",
  "Id_ItemPropertyType_Effect_UndeadDamageMod",
  "Id_ItemPropertyType_Effect_UndeadReductionMod",
  "Id_ItemPropertyType_Effect_WeaponDamage",
  "Id_ItemPropertyType_Effect_WeightLimitBonus",
  "Id_ItemPropertyType_Effect_WeightLimitPenaltyReduce",
]);

export function isPercentStat(propertyType: string): boolean {
  return PERCENT_STATS.has(propertyType);
}

export function formatStatValue(propertyType: string, rawValue: number): string {
  if (PERCENT_STATS.has(propertyType)) {
    const pct = rawValue * 0.1; // raw × 0.001 × 100 = raw × 0.1
    // Remove trailing zeros: 6.0 → 6, 6.2 → 6.2
    const formatted = pct % 1 === 0 ? pct.toFixed(0) : pct.toFixed(1);
    return `${formatted}%`;
  }
  return String(rawValue);
}

export function cleanStatName(raw: string): string {
  return raw
    .replace("Id_ItemPropertyType_Effect_", "")
    .replace(/([A-Z])/g, " $1")
    .trim();
}
