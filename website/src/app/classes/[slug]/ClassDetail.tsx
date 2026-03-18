"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import styles from "./ClassDetail.module.css";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ScalingInfo {
  base_damage: number;
  damage_type: string;
  scaling_pct: number;
  impact_power: number | null;
  formula: string;
}

interface Perk {
  id: string;
  name: string;
  icon?: string;
  description: string;
  is_default: boolean;
  conditions?: string[];
  scaling?: ScalingInfo | null;
}

interface Skill {
  id: string;
  name: string;
  icon?: string;
  description: string;
  skill_type: string;
  skill_tier: number;
  use_moving: boolean;
  scaling?: ScalingInfo | null;
}

interface Spell {
  id: string;
  name: string;
  icon?: string;
  description: string;
  spell_tier: number;
  casting_time: number | null;
  max_count: number | null;
  range: number | null;
  source_type: string;
  cost_type: string;
  casting_type: string;
  bad_range?: number;
  good_range?: number;
  perfect_range?: number;
  tier_effects?: {
    bad?: Record<string, any>;
    good?: Record<string, any>;
    perfect?: Record<string, any>;
  };
  note_count?: number;
  channeling_notes?: number;
  scaling?: ScalingInfo | null;
}

interface Shapeshift {
  id: string;
  name: string;
  icon?: string;
  description: string;
  casting_time: number;
  capsule_radius_scale: number;
  capsule_height_scale: number;
  stat_modifiers?: Record<string, number>;
  form_skill?: string;
  form_skill_description?: string;
}

interface ClassData {
  slug: string;
  name: string;
  icon?: string;
  flavor_text: string;
  role: string;
  base_stats: Record<string, number>;
  derived_stats: {
    health: number;
    move_speed: number;
    move_speed_pct: number;
    action_speed_pct: number;
    spell_casting_speed_pct: number;
    memory_capacity: number;
    magic_resistance_pct: number;
    physical_power: number;
    manual_dexterity_pct: number;
    equip_speed_pct: number;
    buff_duration_pct: number;
    debuff_duration_pct: number;
    regular_interaction_speed_pct: number;
    health_recovery_bonus_pct: number;
  };
  perks: Perk[];
  skills: Skill[];
  spells: Spell[];
  shapeshifts: Shapeshift[];
  usable_item_count: number;
}

interface SpellMergeRecipe {
  result: string;
  result_slug: string;
  sources: string[];
}

interface ClassesJson {
  version: string;
  generated_at: string;
  data: {
    classes: ClassData[];
    spell_merge_recipes: SpellMergeRecipe[];
  };
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const BASE_STAT_META: { key: string; label: string; sub: string }[] = [
  { key: "strength", label: "Strength", sub: "Physical Power" },
  { key: "vigor", label: "Vigor", sub: "Health" },
  { key: "agility", label: "Agility", sub: "Move Speed" },
  { key: "dexterity", label: "Dexterity", sub: "Manual Dexterity" },
  { key: "will", label: "Will", sub: "Magic Resistance" },
  { key: "knowledge", label: "Knowledge", sub: "Spell Casting" },
  { key: "resourcefulness", label: "Resourcefulness", sub: "Utility" },
];

const DERIVED_STAT_META: { key: string; label: string; pct: boolean }[] = [
  { key: "health", label: "Health", pct: false },
  { key: "memory_capacity", label: "Memory Capacity", pct: false },
  { key: "move_speed", label: "Move Speed", pct: false },
  { key: "move_speed_pct", label: "Move Speed %", pct: true },
  { key: "action_speed_pct", label: "Action Speed", pct: true },
  { key: "spell_casting_speed_pct", label: "Spell Casting Speed", pct: true },
  { key: "magic_resistance_pct", label: "Magic Resistance", pct: true },
  { key: "physical_power", label: "Physical Power", pct: false },
  { key: "manual_dexterity_pct", label: "Manual Dexterity", pct: true },
  { key: "equip_speed_pct", label: "Equip Speed", pct: true },
  { key: "buff_duration_pct", label: "Buff Duration", pct: true },
  { key: "debuff_duration_pct", label: "Debuff Duration", pct: true },
  { key: "regular_interaction_speed_pct", label: "Interaction Speed", pct: true },
  { key: "health_recovery_bonus_pct", label: "Health Recovery", pct: true },
  { key: "physical_damage_reduction_pct", label: "Physical Damage Reduction", pct: true },
  { key: "physical_power_bonus_pct", label: "Physical Power Bonus", pct: true },
  { key: "magic_power_bonus_pct", label: "Magic Power Bonus", pct: true },
  { key: "magical_interaction_speed_pct", label: "Magical Interaction Speed", pct: true },
  { key: "spell_recovery_bonus_pct", label: "Spell Recovery Bonus", pct: true },
  { key: "persuasiveness", label: "Persuasiveness", pct: false },
  { key: "cooldown_reduction_pct", label: "Cooldown Reduction", pct: true },
];

const ROLE_STYLE: Record<string, string> = {
  Melee: "roleMelee",
  Caster: "roleCaster",
  Hybrid: "roleHybrid",
};

const SKILL_TYPE_BADGE: Record<string, string> = {
  instant: "badgeInstant",
  channeling: "badgeChanneling",
  memory: "badgeMemory",
};

const SOURCE_TYPE_STYLE: Record<string, string> = {
  fire: "sourceFire",
  ice: "sourceIce",
  lightning: "sourceLightning",
  dark: "sourceDark",
  divine: "sourceDivine",
  spirit: "sourceSpirit",
  arcane: "sourceArcane",
  earth: "sourceEarth",
  water: "sourceWater",
};

/** Strip game markup tags like <PhysicalDamageWeaponPrimary>[0] _</> etc. */
function cleanDescription(raw: string): string {
  // Replace <Tag>[value] text</> patterns with just the value+text
  let cleaned = raw.replace(/<[A-Za-z_.:" =]+>/g, "");
  cleaned = cleaned.replace(/<\/>/g, "");
  // Clean up leftover brackets like [0], [1] etc.
  cleaned = cleaned.replace(/\[(\d+)\]/g, "");
  // Clean up double spaces
  cleaned = cleaned.replace(/ {2,}/g, " ");
  return cleaned.trim();
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ClassDetail({ slug }: { slug: string }) {
  const [classData, setClassData] = useState<ClassData | null>(null);
  const [mergeRecipes, setMergeRecipes] = useState<SpellMergeRecipe[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [expandedPerks, setExpandedPerks] = useState<Set<string>>(new Set());
  const [expandedSkills, setExpandedSkills] = useState<Set<string>>(new Set());
  const [expandedSpells, setExpandedSpells] = useState<Set<string>>(new Set());

  // ── Load class data ──────────────────────────────────────────────────
  const loadData = useCallback(() => {
    setLoading(true);
    setError(false);
    fetch("/data/classes.json")
      .then((r) => {
        if (!r.ok) throw new Error("fetch failed");
        return r.json();
      })
      .then((d: ClassesJson) => {
        const found = d.data.classes.find((c) => c.slug === slug);
        setClassData(found ?? null);
        setMergeRecipes(d.data.spell_merge_recipes ?? []);
        setLoading(false);
      })
      .catch(() => {
        setError(true);
        setLoading(false);
      });
  }, [slug]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // ── Toggle helpers ──────────────────────────────────────────────────
  const togglePerk = useCallback((id: string) => {
    setExpandedPerks((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const toggleSkill = useCallback((id: string) => {
    setExpandedSkills((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const toggleSpell = useCallback((id: string) => {
    setExpandedSpells((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  // ── Loading state ───────────────────────────────────────────────────
  if (loading) {
    return (
      <div className={styles.page}>
        <div className={styles.pageInner}>
          <div className={styles.loading}>Loading...</div>
        </div>
      </div>
    );
  }

  // ── Error state ─────────────────────────────────────────────────────
  if (error) {
    return (
      <div className={styles.page}>
        <div className={styles.pageInner}>
          <div className={styles.errorState}>
            <p className={styles.errorText}>Failed to load class data.</p>
            <button className={styles.retryButton} onClick={loadData}>
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Not found state ─────────────────────────────────────────────────
  if (!classData) {
    return (
      <div className={styles.page}>
        <div className={styles.pageInner}>
          <Link href="/classes" className={styles.breadcrumb}>
            <span className={styles.breadcrumbArrow}>&larr;</span> All Classes
          </Link>
          <div className={styles.notFound}>
            <h1 className={styles.notFoundTitle}>Class Not Found</h1>
            <p className={styles.notFoundDesc}>
              No class matched &ldquo;{slug}&rdquo;.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // ── Computed values ─────────────────────────────────────────────────
  const maxBaseStat = Math.max(
    ...BASE_STAT_META.map((s) => classData.base_stats[s.key] ?? 0)
  );

  const sortedPerks = [...classData.perks].sort((a, b) => {
    if (a.is_default && !b.is_default) return -1;
    if (!a.is_default && b.is_default) return 1;
    return a.name.localeCompare(b.name);
  });

  const sortedSkills = [...classData.skills].sort((a, b) => {
    if (a.skill_tier !== b.skill_tier) return a.skill_tier - b.skill_tier;
    return a.name.localeCompare(b.name);
  });

  // Group spells by tier
  const spellsByTier: Record<number, Spell[]> = {};
  for (const spell of classData.spells) {
    const tier = spell.spell_tier ?? 0;
    if (!spellsByTier[tier]) spellsByTier[tier] = [];
    spellsByTier[tier].push(spell);
  }
  const sortedTiers = Object.keys(spellsByTier)
    .map(Number)
    .sort((a, b) => a - b);

  // For Bard: use "Songs" instead of "Spells"
  const isBard = classData.name === "Bard";
  const isSorcerer = classData.name === "Sorcerer";
  const spellSectionTitle = isBard ? "Songs" : "Spells";

  // Sorcerer merge recipes
  const sorcererRecipes = isSorcerer ? mergeRecipes : [];

  const roleBadgeClass = ROLE_STYLE[classData.role] ?? "roleHybrid";

  // ── Render ──────────────────────────────────────────────────────────
  return (
    <div className={styles.page}>
      <div className={styles.pageInner}>
        {/* === Breadcrumb === */}
        <Link href="/classes" className={styles.breadcrumb}>
          <span className={styles.breadcrumbArrow}>&larr;</span> All Classes
        </Link>

        {/* === Hero Section === */}
        <div className={styles.heroSection}>
          <div className={styles.heroHeader}>
            {classData.icon && (
              <img
                src={classData.icon}
                alt=""
                width={72}
                height={72}
                className={styles.classIcon}
              />
            )}
            <h1 className={styles.className}>{classData.name}</h1>
          </div>
          <div className={styles.tagRow}>
            <span className={styles[roleBadgeClass]}>{classData.role}</span>
          </div>
          {classData.flavor_text && (
            <p className={styles.flavorText}>{classData.flavor_text}</p>
          )}
        </div>

        {/* === Base Stats === */}
        <Divider />
        <h2 className={styles.sectionTitle}>Base Stats</h2>
        <div className={styles.baseStatsSection}>
          {BASE_STAT_META.map(({ key, label, sub }) => {
            const value = classData.base_stats[key] ?? 0;
            const pct = maxBaseStat > 0 ? (value / maxBaseStat) * 100 : 0;
            return (
              <div key={key} className={styles.statBarRow}>
                <span className={styles.statBarLabel}>
                  {label}
                  <span className={styles.statBarLabelSub}>{sub}</span>
                </span>
                <div className={styles.statBarTrack}>
                  <div
                    className={styles.statBarFill}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className={styles.statBarValue}>{value}</span>
              </div>
            );
          })}
        </div>

        {/* === Derived Stats === */}
        <Divider />
        <h2 className={styles.sectionTitle}>Derived Stats</h2>
        <div className={styles.derivedStatsGrid}>
          {DERIVED_STAT_META.map(({ key, label, pct }) => {
            const value =
              (classData.derived_stats as Record<string, number>)[key] ?? 0;
            return (
              <div key={key} className={styles.derivedStatCard}>
                <span className={styles.derivedStatLabel}>{label}</span>
                <span className={getDerivedStatClass(value, pct)}>
                  {formatDerivedStat(value, pct)}
                </span>
              </div>
            );
          })}
        </div>

        {/* === Perks === */}
        <Divider />
        <h2 className={styles.sectionTitle}>
          Perks
          <span className={styles.sectionCount}>
            ({classData.perks.length})
          </span>
        </h2>
        <div className={styles.cardList}>
          {sortedPerks.map((perk) => {
            const open = expandedPerks.has(perk.id);
            return (
              <div
                key={perk.id}
                className={open ? styles.expandCardOpen : styles.expandCard}
              >
                <div
                  className={styles.expandCardHeader}
                  onClick={() => togglePerk(perk.id)}
                >
                  {perk.icon && (
                    <img
                      src={perk.icon}
                      alt=""
                      width={24}
                      height={24}
                      className={styles.abilityIcon}
                    />
                  )}
                  <span className={styles.expandCardName}>{perk.name}</span>
                  {perk.is_default && (
                    <span className={styles.badgeDefault}>Default</span>
                  )}
                  <span
                    className={
                      open
                        ? styles.expandCardChevronOpen
                        : styles.expandCardChevron
                    }
                  >
                    &#9660;
                  </span>
                </div>
                {perk.conditions && perk.conditions.length > 0 && (
                  <div className={styles.conditionRow}>
                    {perk.conditions.map((cond, i) => (
                      <span key={i} className={styles.conditionTag}>
                        {cond}
                      </span>
                    ))}
                  </div>
                )}
                <div
                  className={
                    open ? styles.expandCardBodyOpen : styles.expandCardBody
                  }
                >
                  <div className={styles.expandCardContent}>
                    {cleanDescription(perk.description)}
                    {perk.scaling && (
                      <div className={styles.scalingBox}>
                        <span className={styles.scalingLabel}>Scaling:</span>{" "}
                        {perk.scaling.formula}
                        {perk.scaling.impact_power != null && (
                          <div className={styles.impactPower}>
                            Impact Power: {perk.scaling.impact_power}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* === Skills === */}
        <Divider />
        <h2 className={styles.sectionTitle}>
          Skills
          <span className={styles.sectionCount}>
            ({classData.skills.length})
          </span>
        </h2>
        <div className={styles.cardList}>
          {sortedSkills.map((skill) => {
            const open = expandedSkills.has(skill.id);
            const typeBadgeClass =
              SKILL_TYPE_BADGE[skill.skill_type] ?? "badgeInstant";
            return (
              <div
                key={skill.id}
                className={open ? styles.expandCardOpen : styles.expandCard}
              >
                <div
                  className={styles.expandCardHeader}
                  onClick={() => toggleSkill(skill.id)}
                >
                  {skill.icon && (
                    <img
                      src={skill.icon}
                      alt=""
                      width={24}
                      height={24}
                      className={styles.abilityIcon}
                    />
                  )}
                  <span className={styles.expandCardName}>{skill.name}</span>
                  <span className={styles[typeBadgeClass]}>
                    {skill.skill_type}
                  </span>
                  <span className={styles.badgeTier}>
                    Tier {skill.skill_tier}
                  </span>
                  <span
                    className={
                      open
                        ? styles.expandCardChevronOpen
                        : styles.expandCardChevron
                    }
                  >
                    &#9660;
                  </span>
                </div>
                <div
                  className={
                    open ? styles.expandCardBodyOpen : styles.expandCardBody
                  }
                >
                  <div className={styles.expandCardContent}>
                    <p>{cleanDescription(skill.description)}</p>
                    {skill.use_moving && (
                      <p style={{ marginTop: 8 }}>
                        <span className={styles.badgeMoving}>
                          Can use while moving
                        </span>
                      </p>
                    )}
                    {skill.scaling && (
                      <div className={styles.scalingBox}>
                        <span className={styles.scalingLabel}>Scaling:</span>{" "}
                        {skill.scaling.formula}
                        {skill.scaling.impact_power != null && (
                          <div className={styles.impactPower}>
                            Impact Power: {skill.scaling.impact_power}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* === Spells (only if class has spells) === */}
        {classData.spells.length > 0 && (
          <>
            <Divider />
            <h2 className={styles.sectionTitle}>
              {spellSectionTitle}
              <span className={styles.sectionCount}>
                ({classData.spells.length})
              </span>
            </h2>
            {sortedTiers.map((tier) => (
              <div key={tier} className={styles.tierGroup}>
                <div className={styles.tierHeader}>
                  <span className={styles.tierCircle}>{tier}</span>
                  <span className={styles.tierLabel}>Tier {tier}</span>
                </div>
                <div className={styles.cardList}>
                  {spellsByTier[tier]
                    .sort((a, b) => a.name.localeCompare(b.name))
                    .map((spell) => {
                      const open = expandedSpells.has(spell.id);
                      const srcStyle =
                        SOURCE_TYPE_STYLE[spell.source_type] ?? "sourceDefault";
                      return (
                        <div
                          key={spell.id}
                          className={
                            open ? styles.expandCardOpen : styles.expandCard
                          }
                        >
                          <div
                            className={styles.expandCardHeader}
                            onClick={() => toggleSpell(spell.id)}
                          >
                            {spell.icon && (
                              <img
                                src={spell.icon}
                                alt=""
                                width={24}
                                height={24}
                                className={styles.abilityIcon}
                              />
                            )}
                            <span className={styles.expandCardName}>
                              {spell.name}
                            </span>
                            <span className={styles[srcStyle]}>
                              {spell.source_type}
                            </span>
                            {spell.cost_type && (
                              <span className={styles.badgeTier}>
                                {spell.cost_type}
                              </span>
                            )}
                            <span
                              className={
                                open
                                  ? styles.expandCardChevronOpen
                                  : styles.expandCardChevron
                              }
                            >
                              &#9660;
                            </span>
                          </div>
                          <div
                            className={
                              open
                                ? styles.expandCardBodyOpen
                                : styles.expandCardBody
                            }
                          >
                            <div className={styles.expandCardContent}>
                              <div className={styles.spellMeta}>
                                {spell.casting_time != null && (
                                  <span className={styles.spellMetaItem}>
                                    Cast Time:{" "}
                                    <span className={styles.spellMetaValue}>
                                      {spell.casting_time}s
                                    </span>
                                  </span>
                                )}
                                {spell.max_count != null &&
                                  spell.max_count > 0 && (
                                    <span className={styles.spellMetaItem}>
                                      Max Count:{" "}
                                      <span className={styles.spellMetaValue}>
                                        {spell.max_count}
                                      </span>
                                    </span>
                                  )}
                                {spell.range != null && spell.range > 0 && (
                                  <span className={styles.spellMetaItem}>
                                    Range:{" "}
                                    <span className={styles.spellMetaValue}>
                                      {spell.range}
                                    </span>
                                  </span>
                                )}
                                <span className={styles.spellMetaItem}>
                                  Type:{" "}
                                  <span className={styles.spellMetaValue}>
                                    {spell.casting_type}
                                  </span>
                                </span>
                                {spell.note_count != null &&
                                  spell.note_count > 0 && (
                                    <span className={styles.spellMetaItem}>
                                      Notes:{" "}
                                      <span className={styles.spellMetaValue}>
                                        {spell.note_count}
                                        {spell.channeling_notes != null &&
                                          spell.channeling_notes > 0 &&
                                          ` (+${spell.channeling_notes} channeling)`}
                                      </span>
                                    </span>
                                  )}
                              </div>
                              <p>{cleanDescription(spell.description)}</p>

                              {spell.scaling && (
                                <div className={styles.scalingBox}>
                                  <span className={styles.scalingLabel}>Scaling:</span>{" "}
                                  {spell.scaling.formula}
                                  {spell.scaling.impact_power != null && (
                                    <div className={styles.impactPower}>
                                      Impact Power: {spell.scaling.impact_power}
                                    </div>
                                  )}
                                </div>
                              )}

                              {/* Bard Song Tier Effects */}
                              {spell.tier_effects && (
                                <table className={styles.tierTable}>
                                  <thead>
                                    <tr>
                                      <th>Tier</th>
                                      <th>Range</th>
                                      <th>Duration</th>
                                      <th>Effect</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {(
                                      ["bad", "good", "perfect"] as const
                                    ).map((tier) => {
                                      const fx =
                                        spell.tier_effects?.[tier];
                                      if (!fx) return null;
                                      const rangeVal =
                                        tier === "bad"
                                          ? spell.bad_range
                                          : tier === "good"
                                            ? spell.good_range
                                            : spell.perfect_range;
                                      const { duration, description } =
                                        summarizeTierEffect(
                                          fx,
                                          cleanDescription(
                                            spell.description
                                          )
                                        );
                                      const tierClass =
                                        tier === "bad"
                                          ? styles.tierBad
                                          : tier === "good"
                                            ? styles.tierGood
                                            : styles.tierPerfect;
                                      return (
                                        <tr key={tier}>
                                          <td className={tierClass}>
                                            {tier.charAt(0).toUpperCase() +
                                              tier.slice(1)}
                                          </td>
                                          <td>
                                            {rangeVal != null
                                              ? gameUnitsToMeters(rangeVal)
                                              : "--"}
                                          </td>
                                          <td>{duration ?? "--"}</td>
                                          <td>{description}</td>
                                        </tr>
                                      );
                                    })}
                                  </tbody>
                                </table>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                </div>
              </div>
            ))}

            {/* Sorcerer Spell Merge Recipes */}
            {sorcererRecipes.length > 0 && (
              <div className={styles.mergeSection}>
                <h3 className={styles.sectionTitle}>Spell Merge Recipes</h3>
                {sorcererRecipes.map((recipe) => (
                  <div key={recipe.result_slug} className={styles.mergeCard}>
                    <span className={styles.mergeResult}>
                      {recipe.result}
                    </span>
                    <span className={styles.mergeArrow}>&larr;</span>
                    {recipe.sources.map((src, i) => (
                      <span key={i}>
                        {i > 0 && (
                          <span className={styles.mergePlus}> + </span>
                        )}
                        <span className={styles.mergeSource}>{src}</span>
                      </span>
                    ))}
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {/* === Shapeshifts (Druid only) === */}
        {classData.shapeshifts.length > 0 && (
          <>
            <Divider />
            <h2 className={styles.sectionTitle}>
              Shapeshift Forms
              <span className={styles.sectionCount}>
                ({classData.shapeshifts.length})
              </span>
            </h2>
            {classData.shapeshifts.map((form) => (
              <div key={form.id} className={styles.shapeshiftCard}>
                <div className={styles.shapeshiftHeader}>
                  {form.icon && (
                    <img
                      src={form.icon}
                      alt=""
                      width={32}
                      height={32}
                      className={styles.shapeshiftIcon}
                    />
                  )}
                  <h3 className={styles.shapeshiftName}>{form.name}</h3>
                </div>
                <div className={styles.shapeshiftMeta}>
                  <span className={styles.shapeshiftMetaItem}>
                    Cast Time:{" "}
                    <span className={styles.shapeshiftMetaValue}>
                      {form.casting_time}s
                    </span>
                  </span>
                  <span className={styles.shapeshiftMetaItem}>
                    Size:{" "}
                    <span className={styles.shapeshiftMetaValue}>
                      {form.capsule_radius_scale}x radius,{" "}
                      {form.capsule_height_scale}x height
                    </span>
                  </span>
                </div>
                <p className={styles.shapeshiftDesc}>
                  {cleanDescription(form.description)}
                </p>

                {/* Stat Modifiers */}
                {form.stat_modifiers &&
                  Object.keys(form.stat_modifiers).length > 0 && (
                    <ul className={styles.statModifiers}>
                      {Object.entries(form.stat_modifiers).map(([k, v]) => (
                        <li
                          key={k}
                          className={
                            v >= 0
                              ? styles.statModPositive
                              : styles.statModNegative
                          }
                        >
                          {formatStatModValue(k, v)} {formatStatModKey(k)}
                        </li>
                      ))}
                    </ul>
                  )}

                {/* Form Skill */}
                {form.form_skill && (
                  <div className={styles.formSkill}>
                    <span className={styles.formSkillLabel}>Form Skill:</span>
                    <span className={styles.formSkillName}>
                      {form.form_skill}
                    </span>
                    {form.form_skill_description && (
                      <p className={styles.formSkillDesc}>
                        {cleanDescription(form.form_skill_description)}
                      </p>
                    )}
                  </div>
                )}
              </div>
            ))}
          </>
        )}

        {/* === Equipment === */}
        <Divider />
        <h2 className={styles.sectionTitle}>Equipment</h2>
        <div className={styles.equipmentCard}>
          <span className={styles.equipmentCount}>
            Can equip{" "}
            <span className={styles.equipmentCountValue}>
              {classData.usable_item_count}
            </span>{" "}
            items
          </span>
          <Link
            href={`/items?class=${encodeURIComponent(classData.name)}`}
            className={styles.equipmentLink}
          >
            Browse Items &rarr;
          </Link>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function Divider() {
  return (
    <div className={styles.sectionDivider}>
      <div className={styles.dividerLineRight} />
      <div className={styles.dividerDiamond} />
      <div className={styles.dividerLine} />
    </div>
  );
}

function formatDerivedStat(value: number, isPct: boolean): string {
  if (isPct) {
    const sign = value > 0 ? "+" : "";
    return `${sign}${value}%`;
  }
  return String(value);
}

function getDerivedStatClass(value: number, isPct: boolean): string {
  if (value === 0) return styles.derivedStatValueZero;
  if (isPct && value > 0) return styles.derivedStatValuePositive;
  if (isPct && value < 0) return styles.derivedStatValueNegative;
  return styles.derivedStatValue;
}

/** Convert stat modifier keys like `max_health_pct` → "Max Health" */
function formatStatModKey(key: string): string {
  // Remove trailing _pct suffix (we show % separately)
  const cleaned = key.replace(/_pct$/, "");
  return cleaned
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

/** Format a stat modifier value: "+50%" or "-20%" */
function formatStatModValue(key: string, value: number): string {
  const sign = value > 0 ? "+" : "";
  const suffix = key.endsWith("_pct") ? "%" : "";
  return `${sign}${value}${suffix}`;
}

/** Convert game units to meters (divide by 100) */
function gameUnitsToMeters(units: number): string {
  const meters = units / 100;
  // Avoid floating point artifacts
  return `${parseFloat(meters.toFixed(2))}m`;
}

/** Convert milliseconds to a duration string (always seconds, 2 decimal places) */
function msToDuration(ms: number): string {
  const seconds = ms / 1000;
  return `${seconds.toFixed(2)}s`;
}

/** Property key -> human-readable display name for tier effects */
const TIER_EFFECT_DISPLAY_NAMES: Record<string, string> = {
  ExecMagicalDamageBase: "Magical Damage",
  ExecPhysicalDamageBase: "Physical Damage",
  ExecAttributeBonusRatio: "Power Scaling",
  ExecRecoveryHealBase: "Recovery Heal",
  ActionSpeed: "Action Speed",
  SpellCastingSpeed: "Spell Casting Speed",
  MoveSpeedAdd: "Move Speed",
  MoveSpeedMod: "Move Speed",
  ArmorRating: "Armor Rating",
  MagicResistance: "Magic Resistance",
  PhysicalPower: "Physical Power",
  StrengthBase: "Strength",
  VigorBase: "Vigor",
  AgilityBase: "Agility",
  DexterityBase: "Dexterity",
  WillBase: "Will",
  KnowledgeBase: "Knowledge",
  ResourcefulnessBase: "Resourcefulness",
  MaxHealthMod: "Max Health",
  PhysicalReductionMod: "Physical Reduction",
  PhysicalDamageWeapon: "Physical Damage",
  MagicalDamageMod: "Magical Damage",
  ExecImpactPower: "Impact Power",
};

/** Properties that display with % suffix (percentage-based values) */
const PERCENT_PROPERTIES = new Set([
  "ActionSpeed", "SpellCastingSpeed", "MoveSpeedMod",
  "MaxHealthMod", "PhysicalReductionMod", "MagicalDamageMod",
  "ExecAttributeBonusRatio",
]);

function tierEffectDisplayName(key: string): string {
  if (key in TIER_EFFECT_DISPLAY_NAMES) return TIER_EFFECT_DISPLAY_NAMES[key];
  // Fallback: CamelCase to spaced words
  return key
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/([A-Z]+)([A-Z][a-z])/g, "$1 $2");
}

/** Format a tier effect value with appropriate suffix */
function formatTierValue(key: string, value: number): string {
  const sign = value > 0 ? "+" : "";
  if (PERCENT_PROPERTIES.has(key)) {
    // Values already scaled by build_classes.py (÷10)
    return `${sign}${value}%`;
  }
  // Flat values: no suffix
  return `${sign}${value}`;
}

/** Summarise a tier_effects entry into duration + human-readable effect string.
 *  If only duration is present (e.g., Song of Shadow), returns the
 *  song description summary from the parent spell instead of "--".
 */
function summarizeTierEffect(
  effect: Record<string, any>,
  songDescription?: string
): {
  duration: string | null;
  description: string;
} {
  const parts: string[] = [];
  let duration: string | null = null;

  for (const [k, v] of Object.entries(effect)) {
    // Extract duration_ms separately for the Duration column
    if (k === "duration_ms" && typeof v === "number") {
      duration = msToDuration(v);
      continue;
    }
    // Legacy key check (in case data uses "duration" directly)
    if (k === "duration" && typeof v === "number") {
      duration = msToDuration(v);
      continue;
    }
    const label = tierEffectDisplayName(k);
    if (typeof v === "number") {
      parts.push(`${formatTierValue(k, v)} ${label}`);
    } else {
      parts.push(`${label}: ${String(v)}`);
    }
  }

  // If no gameplay properties (only duration), use song description as summary
  if (parts.length === 0 && songDescription) {
    // Take first sentence of the song description as a brief summary
    const firstSentence = songDescription.split(".")[0];
    return { duration, description: firstSentence || "\u2014" };
  }

  return { duration, description: parts.join(", ") || "\u2014" };
}
