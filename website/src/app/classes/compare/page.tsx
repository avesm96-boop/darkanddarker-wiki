"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import Link from "next/link";
import styles from "./compare.module.css";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface BaseStats {
  strength: number;
  vigor: number;
  agility: number;
  dexterity: number;
  will: number;
  knowledge: number;
  resourcefulness: number;
}

interface DerivedStats {
  health: number;
  move_speed: number;
  [key: string]: number;
}

interface Perk {
  id: string;
  name: string;
  description: string;
  icon?: string;
}

interface Skill {
  id: string;
  name: string;
  description: string;
  icon?: string;
}

interface Spell {
  id: string;
  name: string;
  description: string;
  icon?: string;
}

interface GameClass {
  slug: string;
  name: string;
  icon?: string;
  flavor_text: string;
  role: string;
  base_stats: BaseStats;
  derived_stats: DerivedStats;
  perks: Perk[];
  skills: Skill[];
  spells: Spell[];
}

interface ClassesDataRaw {
  version: string;
  generated_at: string;
  data: {
    classes: GameClass[];
  };
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const STAT_KEYS: (keyof BaseStats)[] = [
  "strength",
  "vigor",
  "agility",
  "dexterity",
  "will",
  "knowledge",
  "resourcefulness",
];

const STAT_LABELS: Record<keyof BaseStats, string> = {
  strength: "Strength",
  vigor: "Vigor",
  agility: "Agility",
  dexterity: "Dexterity",
  will: "Will",
  knowledge: "Knowledge",
  resourcefulness: "Resource",
};

const DERIVED_STAT_KEYS: string[] = [
  "health",
  "move_speed",
  "action_speed_pct",
  "spell_casting_speed_pct",
  "memory_capacity",
  "magic_resistance_pct",
  "physical_power",
  "physical_power_bonus_pct",
  "magic_power_bonus_pct",
  "manual_dexterity_pct",
  "equip_speed_pct",
  "buff_duration_pct",
  "debuff_duration_pct",
  "regular_interaction_speed_pct",
  "health_recovery_bonus_pct",
  "physical_damage_reduction_pct",
  "magical_interaction_speed_pct",
  "spell_recovery_bonus_pct",
  "persuasiveness",
  "cooldown_reduction_pct",
];

const DERIVED_STAT_LABELS: Record<string, string> = {
  health: "Health",
  move_speed: "Move Speed",
  move_speed_pct: "Move Speed %",
  action_speed_pct: "Action Speed %",
  spell_casting_speed_pct: "Spell Casting Speed %",
  memory_capacity: "Memory Capacity",
  magic_resistance_pct: "Magic Resistance %",
  physical_power: "Physical Power",
  physical_power_bonus_pct: "Physical Power Bonus %",
  magic_power_bonus_pct: "Magic Power Bonus %",
  manual_dexterity_pct: "Manual Dexterity %",
  equip_speed_pct: "Equip Speed %",
  buff_duration_pct: "Buff Duration %",
  debuff_duration_pct: "Debuff Duration %",
  regular_interaction_speed_pct: "Interaction Speed %",
  health_recovery_bonus_pct: "Health Recovery %",
  physical_damage_reduction_pct: "Phys. Dmg Reduction %",
  magical_interaction_speed_pct: "Magic Interact Speed %",
  spell_recovery_bonus_pct: "Spell Recovery %",
  persuasiveness: "Persuasiveness",
  cooldown_reduction_pct: "Cooldown Reduction %",
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatStat(value: number): string {
  if (Number.isInteger(value)) return String(value);
  return value.toFixed(1);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ComparePage() {
  const [classes, setClasses] = useState<GameClass[] | null>(null);
  const [error, setError] = useState(false);
  const [classASlug, setClassASlug] = useState("fighter");
  const [classBSlug, setClassBSlug] = useState("barbarian");

  const loadData = useCallback(() => {
    setError(false);
    setClasses(null);
    fetch("/data/classes.json")
      .then((r) => {
        if (!r.ok) throw new Error("fetch failed");
        return r.json();
      })
      .then((json: ClassesDataRaw) => {
        setClasses(json.data.classes);
      })
      .catch(() => setError(true));
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const classA = useMemo(
    () => classes?.find((c) => c.slug === classASlug) ?? null,
    [classes, classASlug]
  );
  const classB = useMemo(
    () => classes?.find((c) => c.slug === classBSlug) ?? null,
    [classes, classBSlug]
  );

  // Max base stat across both selected classes for bar normalization
  const maxBaseStat = useMemo(() => {
    if (!classA || !classB) return 25;
    let max = 0;
    for (const key of STAT_KEYS) {
      if (classA.base_stats[key] > max) max = classA.base_stats[key];
      if (classB.base_stats[key] > max) max = classB.base_stats[key];
    }
    return max || 25;
  }, [classA, classB]);

  // Unique perks
  const uniquePerksA = useMemo(() => {
    if (!classA || !classB) return [];
    const bIds = new Set(classB.perks.map((p) => p.id));
    return classA.perks.filter((p) => !bIds.has(p.id));
  }, [classA, classB]);

  const uniquePerksB = useMemo(() => {
    if (!classA || !classB) return [];
    const aIds = new Set(classA.perks.map((p) => p.id));
    return classB.perks.filter((p) => !aIds.has(p.id));
  }, [classA, classB]);

  // -- Loading --
  if (!classes && !error) {
    return (
      <div className={styles.page}>
        <div className={`container ${styles.pageInner}`}>
          <div className="section-head">
            <span className="section-label">Toolkit</span>
            <h1 className="section-title">Compare Classes</h1>
          </div>
          <div className={styles.loadingState}>Loading class data...</div>
        </div>
      </div>
    );
  }

  // -- Error --
  if (error) {
    return (
      <div className={styles.page}>
        <div className={`container ${styles.pageInner}`}>
          <div className="section-head">
            <span className="section-label">Toolkit</span>
            <h1 className="section-title">Compare Classes</h1>
          </div>
          <div className={styles.errorState}>
            <p className={styles.errorText}>Failed to load class data</p>
            <button className={styles.retryButton} onClick={loadData}>
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!classA || !classB || !classes) return null;

  return (
    <div className={styles.page}>
      <div className={`container ${styles.pageInner}`}>
        {/* Back Link */}
        <Link href="/classes" className={styles.backLink}>
          &larr; All Classes
        </Link>

        {/* Header */}
        <div className="section-head" style={{ marginBottom: "36px" }}>
          <span className="section-label">Toolkit</span>
          <h1 className="section-title">Compare Classes</h1>
          <p className="section-desc">
            Side-by-side comparison of base stats, derived stats, and abilities.
          </p>
          <div className={styles.headerDivider} />
        </div>

        {/* Class Selectors */}
        <div className={styles.selectorArea}>
          <div className={styles.classSelector}>
            {classA.icon && (
              <img
                src={classA.icon}
                alt=""
                className={styles.classIconPreview}
              />
            )}
            <select
              className={styles.classSelect}
              value={classASlug}
              onChange={(e) => setClassASlug(e.target.value)}
            >
              {classes.map((c) => (
                <option key={c.slug} value={c.slug}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>

          <span className={styles.vsLabel}>VS</span>

          <div className={styles.classSelector}>
            {classB.icon && (
              <img
                src={classB.icon}
                alt=""
                className={styles.classIconPreview}
              />
            )}
            <select
              className={styles.classSelect}
              value={classBSlug}
              onChange={(e) => setClassBSlug(e.target.value)}
            >
              {classes.map((c) => (
                <option key={c.slug} value={c.slug}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Base Stats — Mirrored Bar Chart */}
        <div
          className={`${styles.section} ${styles.fadeIn}`}
          style={{ animationDelay: "0ms" }}
        >
          <h2 className={styles.sectionTitle}>Base Stats</h2>

          <div className={styles.barChartHeader}>
            <div
              className={`${styles.barChartHeaderName} ${styles.barChartHeaderLeft}`}
            >
              {classA.name}
            </div>
            <div className={styles.barChartHeaderCenter} />
            <div
              className={`${styles.barChartHeaderName} ${styles.barChartHeaderRight}`}
            >
              {classB.name}
            </div>
          </div>

          <div className={styles.barChart}>
            {STAT_KEYS.map((statKey) => {
              const valA = classA.base_stats[statKey];
              const valB = classB.base_stats[statKey];
              const pctA = Math.round((valA / maxBaseStat) * 100);
              const pctB = Math.round((valB / maxBaseStat) * 100);
              const aHigher = valA > valB;
              const bHigher = valB > valA;
              const equal = valA === valB;

              return (
                <div key={statKey} className={styles.barRow}>
                  {/* Left side — Class A */}
                  <div className={styles.barLeft}>
                    <span
                      className={`${styles.barValueLeft} ${
                        equal
                          ? styles.barValueEqual
                          : aHigher
                          ? styles.barValueHighlight
                          : styles.barValueDim
                      }`}
                    >
                      {valA}
                    </span>
                    <div className={styles.barTrackLeft}>
                      <div
                        className={`${styles.barFillLeft} ${
                          !aHigher && !equal ? styles.barFillDim : ""
                        }`}
                        style={{ width: `${pctA}%` }}
                      />
                    </div>
                  </div>

                  {/* Center label */}
                  <span className={styles.barStatLabel}>
                    {STAT_LABELS[statKey]}
                  </span>

                  {/* Right side — Class B */}
                  <div className={styles.barRight}>
                    <div className={styles.barTrackRight}>
                      <div
                        className={`${styles.barFillRight} ${
                          !bHigher && !equal ? styles.barFillDim : ""
                        }`}
                        style={{ width: `${pctB}%` }}
                      />
                    </div>
                    <span
                      className={`${styles.barValueRight} ${
                        equal
                          ? styles.barValueEqual
                          : bHigher
                          ? styles.barValueHighlight
                          : styles.barValueDim
                      }`}
                    >
                      {valB}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Derived Stats Table */}
        <div
          className={`${styles.section} ${styles.fadeIn}`}
          style={{ animationDelay: "100ms" }}
        >
          <h2 className={styles.sectionTitle}>Derived Stats</h2>
          <table className={styles.derivedTable}>
            <thead>
              <tr>
                <th>Stat</th>
                <th>{classA.name}</th>
                <th>{classB.name}</th>
              </tr>
            </thead>
            <tbody>
              {DERIVED_STAT_KEYS.map((key) => {
                const valA = classA.derived_stats[key] ?? 0;
                const valB = classB.derived_stats[key] ?? 0;
                const aHigher = valA > valB;
                const bHigher = valB > valA;
                const equal = valA === valB;

                return (
                  <tr key={key}>
                    <td>{DERIVED_STAT_LABELS[key] ?? key}</td>
                    <td
                      className={
                        equal
                          ? styles.cellEqual
                          : aHigher
                          ? styles.cellHighlight
                          : styles.cellDim
                      }
                    >
                      {formatStat(valA)}
                    </td>
                    <td
                      className={
                        equal
                          ? styles.cellEqual
                          : bHigher
                          ? styles.cellHighlight
                          : styles.cellDim
                      }
                    >
                      {formatStat(valB)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Abilities Summary */}
        <div
          className={`${styles.section} ${styles.fadeIn}`}
          style={{ animationDelay: "200ms" }}
        >
          <h2 className={styles.sectionTitle}>Abilities Summary</h2>
          <div className={styles.abilitySummary}>
            {/* Counts */}
            {(
              [
                ["Perks", classA.perks.length, classB.perks.length],
                ["Skills", classA.skills.length, classB.skills.length],
                ["Spells", classA.spells.length, classB.spells.length],
              ] as [string, number, number][]
            ).map(([label, countA, countB]) => (
              <div key={label} className={styles.abilityCountRow}>
                <span
                  className={styles.abilityCountLeft}
                  style={{
                    color:
                      countA > countB
                        ? "var(--gold-300)"
                        : countA === countB
                        ? "var(--text-dim)"
                        : "var(--text-muted)",
                  }}
                >
                  {countA} {label}
                </span>
                <span className={styles.abilityCountLabel}>vs</span>
                <span
                  className={styles.abilityCountRight}
                  style={{
                    color:
                      countB > countA
                        ? "var(--gold-300)"
                        : countA === countB
                        ? "var(--text-dim)"
                        : "var(--text-muted)",
                  }}
                >
                  {countB} {label}
                </span>
              </div>
            ))}

            {/* Unique Perks */}
            <div className={styles.uniqueAbilitiesSection}>
              <div className={styles.uniqueAbilitiesTitle}>Unique Perks</div>
              <div className={styles.uniqueAbilitiesGrid}>
                <div className={styles.uniqueAbilitiesColumn}>
                  <div className={styles.uniqueAbilitiesColumnHeader}>
                    {classA.name} only
                  </div>
                  {uniquePerksA.length === 0 ? (
                    <div className={styles.noUnique}>None</div>
                  ) : (
                    uniquePerksA.map((p) => (
                      <div key={p.id} className={styles.uniqueAbilityItem}>
                        {p.icon && (
                          <img
                            src={p.icon}
                            alt=""
                            className={styles.uniqueAbilityIcon}
                          />
                        )}
                        <span>{p.name}</span>
                      </div>
                    ))
                  )}
                </div>
                <div className={styles.uniqueAbilitiesColumn}>
                  <div className={styles.uniqueAbilitiesColumnHeader}>
                    {classB.name} only
                  </div>
                  {uniquePerksB.length === 0 ? (
                    <div className={styles.noUnique}>None</div>
                  ) : (
                    uniquePerksB.map((p) => (
                      <div key={p.id} className={styles.uniqueAbilityItem}>
                        {p.icon && (
                          <img
                            src={p.icon}
                            alt=""
                            className={styles.uniqueAbilityIcon}
                          />
                        )}
                        <span>{p.name}</span>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Quick Links */}
        <div
          className={`${styles.section} ${styles.fadeIn}`}
          style={{ animationDelay: "300ms" }}
        >
          <h2 className={styles.sectionTitle}>Quick Links</h2>
          <div className={styles.quickLinks}>
            <Link
              href={`/classes/${classA.slug}`}
              className={styles.quickLink}
            >
              {classA.icon && (
                <img
                  src={classA.icon}
                  alt=""
                  className={styles.quickLinkIcon}
                />
              )}
              View {classA.name}
            </Link>
            <Link
              href={`/classes/${classB.slug}`}
              className={styles.quickLink}
            >
              {classB.icon && (
                <img
                  src={classB.icon}
                  alt=""
                  className={styles.quickLinkIcon}
                />
              )}
              View {classB.name}
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
