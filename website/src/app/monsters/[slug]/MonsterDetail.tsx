"use client";

import { useState, useEffect, useCallback } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import styles from "./MonsterDetail.module.css";

const ModelViewer = dynamic(() => import("./ModelViewer"), { ssr: false });

// CDN base URL for large assets (3D models, map tiles)
const CDN_BASE = "https://pub-fd64511c60894919bcb1e9967b471c7f.r2.dev";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface MonsterGrade {
  adv_point: number;
  exp_point: number;
  stats: Record<string, number>;
  combos?: Combo[];
  abilities?: string[];
}

interface Attack {
  name: string;
  damage_ratio: number;
  impact_power: number;
}

interface Combo {
  from: string;
  to: string;
  from_animation_id?: string | null;
  to_animation_id?: string | null;
}

interface StatusEffect {
  name: string;
  icon: string;
  tags: string[];
}

interface LootDrop {
  name: string;
  quantity: number;
}

interface HuntingLoot {
  name: string;
  rarity: string;
  description: string;
}

interface Projectile {
  name: string;
}

interface AoeDef {
  name: string;
}

interface Monster {
  slug: string;
  name: string;
  class_type: string;
  creature_types: string[];
  image: string;
  dungeons: string[];
  spawn_locations?: { dungeon: string; module: string }[];
  grades: Record<string, MonsterGrade>;
  attacks: Attack[];
  status_effects?: StatusEffect[];
  loot?: LootDrop[];
  hunting_loot?: HuntingLoot;
  projectiles?: Projectile[];
  aoe?: AoeDef[];
}

interface MonstersData {
  version: string;
  generated_at: string;
  data: Monster[];
}

export interface ComboPlayback {
  animations: string[];
  onComplete?: () => void;
}

// Guide types
// All guide sub-items support an optional `grades` field:
//   - omitted or empty → applies to ALL grades
//   - ["Common", "Elite"] → only shown when that grade is selected
//   - ["Nightmare"] → only shown for Nightmare (grade-exclusive content)

interface GuidePhase {
  name: string;
  description: string;
  icon: string;
  grades?: string[];
}

interface GuideAttackEntry {
  name: string;
  ratio?: number;
  damage_ratio?: number;
  damage_common: number;
  damage_elite: number;
  damage_nightmare?: number;
  note: string;
  grades?: string[];
}

interface GuideAttackCategory {
  tier: string;
  color: string;
  attacks: GuideAttackEntry[];
  grades?: string[];
}

interface GuideComboChain {
  from: string;
  to: string[];
  note: string;
  grades?: string[];
}

interface GuideStatusDetail {
  name: string;
  type: string;
  duration: string;
  stacks: number;
  description: string;
  counter: string;
  grades?: string[];
}

interface GuideStrategy {
  title: string;
  priority: string;
  description: string;
  grades?: string[];
}

interface GuideData {
  slug: string;
  overview: string;
  phases: GuidePhase[];
  attack_categories: GuideAttackCategory[];
  combo_flow: { description: string; chains: GuideComboChain[] };
  status_effects_detail: GuideStatusDetail[];
  strategies: GuideStrategy[];
  elite_differences: string[];
  ai_perception: {
    vision_angle: number;
    vision_description: string;
    damage_sense: boolean;
    damage_description: string;
    hearing: boolean;
    hearing_description: string;
    stuck_tracking: boolean;
    stuck_description: string;
    sight_radius?: number;
    lose_sight_radius?: number | null;
    sight_description?: string;
  };
}

/** Returns true if an item with an optional grades[] field should be shown for the current grade */
function matchesGrade(item: { grades?: string[] }, grade: string): boolean {
  if (!item.grades || item.grades.length === 0) return true;
  return item.grades.includes(grade);
}

/** Returns true if an item is exclusive to certain grades (not available in all) */
function isGradeExclusive(item: { grades?: string[] }): boolean {
  return !!item.grades && item.grades.length > 0;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const STAT_LABELS: Record<string, string> = {
  MaxHealthAdd: "Health",
  PhysicalDamageWeapon: "Physical Damage",
  MoveSpeedBase: "Move Speed",
  ActionSpeed: "Action Speed",
  StrengthBase: "Strength",
  VigorBase: "Vigor",
  AgilityBase: "Agility",
  DexterityBase: "Dexterity",
  WillBase: "Will",
  KnowledgeBase: "Knowledge",
  ResourcefulnessBase: "Resourcefulness",
  MagicResistance: "Magic Resistance",
  MagicalReduction: "Magical Reduction",
  FireMagicalReduction: "Fire Reduction",
  IceMagicalReduction: "Ice Reduction",
  LightMagicalReduction: "Light Reduction",
  DarkMagicalReduction: "Dark Reduction",
  DivineMagicalReduction: "Divine Reduction",
  EvilMagicalReduction: "Evil Reduction",
  EarthMagicalReduction: "Earth Reduction",
  ProjectileReductionMod: "Projectile Reduction",
  ImpactResistance: "Impact Resistance",
  MaxImpactEndurance: "Impact Endurance",
};

const KEY_STAT_LABELS: Record<string, string> = {
  MaxHealthAdd: "HP",
  PhysicalDamageWeapon: "DMG",
  MoveSpeedBase: "SPD",
  ActionSpeed: "ASPD",
};

const KEY_STATS = ["MaxHealthAdd", "PhysicalDamageWeapon", "MoveSpeedBase", "ActionSpeed"];

const ATTRIBUTE_STATS = [
  "StrengthBase", "VigorBase", "AgilityBase", "DexterityBase",
  "WillBase", "KnowledgeBase", "ResourcefulnessBase",
];

const RESISTANCE_STATS = [
  "MagicResistance", "MagicalReduction",
  "FireMagicalReduction", "IceMagicalReduction", "LightMagicalReduction",
  "DarkMagicalReduction", "DivineMagicalReduction", "EvilMagicalReduction",
  "EarthMagicalReduction", "ProjectileReductionMod",
  "ImpactResistance", "MaxImpactEndurance",
];

const GRADE_COLORS: Record<string, string> = {
  Common: "var(--rarity-common)",
  Elite: "var(--gold-500)",
  Nightmare: "var(--red-300)",
};

const CLASS_BADGE_STYLE: Record<string, string> = {
  Normal: "classBadgeNormal",
  SubBoss: "classBadgeSubBoss",
  Boss: "classBadgeBoss",
};

const CLASS_LABELS: Record<string, string> = {
  Normal: "Normal",
  SubBoss: "Sub-Boss",
  Boss: "Boss",
};

const RARITY_COLORS: Record<string, string> = {
  Common: "var(--rarity-common)",
  Uncommon: "#1eff00",
  Rare: "#0070dd",
  Epic: "var(--gold-500)",
  Legendary: "#ff8000",
  Unique: "#e6cc80",
};

type TabId = "stats" | "attacks" | "combos" | "loot" | "abilities" | "behavior" | "strategy" | "animations";

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function MonsterDetail({ slug }: { slug: string }) {
  const [monster, setMonster] = useState<Monster | null>(null);
  const [loading, setLoading] = useState(true);
  const [grade, setGrade] = useState<string>("Common");
  const [activeTab, setActiveTab] = useState<TabId>("behavior");
  const [tabInitialized, setTabInitialized] = useState(false);
  const [hasModel, setHasModel] = useState(false);
  const [comboPlayback, setComboPlayback] = useState<ComboPlayback | null>(null);
  const [playingComboIdx, setPlayingComboIdx] = useState<number | null>(null);
  const [guide, setGuide] = useState<GuideData | null>(null);
  const [animDefs, setAnimDefs] = useState<{ id: string; label: string; file: string; loop: boolean }[]>([]);
  const [activeAnim, setActiveAnim] = useState<{ id: string; label: string; file: string; loop: boolean } | null>(null);

  const gradeVariant = grade.toLowerCase();
  const variantModelUrl = `${CDN_BASE}/monster-models/animations/${slug}/${slug}-${gradeVariant}.glb`;
  const modelUrl = `${CDN_BASE}/monster-models/${slug}.glb`;
  const animBasePath = `${CDN_BASE}/monster-models/animations/${slug}`;
  const [activeModelUrl, setActiveModelUrl] = useState(modelUrl);

  // ── Load monster data ──────────────────────────────────────────────────
  useEffect(() => {
    fetch("/data/monsters.json")
      .then((r) => r.json())
      .then((d: MonstersData) => {
        const found = d.data.find((m) => m.slug === slug);
        setMonster(found ?? null);
        if (found) {
          const grades = Object.keys(found.grades);
          setGrade(grades.includes("Common") ? "Common" : grades[0]);
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [slug]);

  // ── Check for 3D model ─────────────────────────────────────────────────
  useEffect(() => {
    fetch(modelUrl, { method: "HEAD" })
      .then((r) => setHasModel(r.ok))
      .catch(() => setHasModel(false));
  }, [modelUrl]);

  // ── Switch model when grade changes ──────────────────────────────────
  useEffect(() => {
    const variant = grade.toLowerCase();
    const varUrl = `${CDN_BASE}/monster-models/animations/${slug}/${slug}-${variant}.glb`;
    fetch(varUrl, { method: "HEAD" })
      .then((r) => {
        if (r.ok) {
          setActiveModelUrl(varUrl);
        } else {
          setActiveModelUrl(modelUrl);
        }
      })
      .catch(() => setActiveModelUrl(modelUrl));
  }, [grade, slug, modelUrl]);

  // ── Load guide data (if available) ──────────────────────────────────
  useEffect(() => {
    fetch(`/data/guides/${slug}.json`)
      .then((r) => { if (!r.ok) throw new Error("no guide"); return r.json(); })
      .then((d: GuideData) => setGuide(d))
      .catch(() => {});
  }, [slug]);

  // ── Load animation manifest ────────────────────────────────────────
  useEffect(() => {
    if (!animBasePath) return;
    fetch(`${animBasePath}/manifest.json`)
      .then(r => { if (!r.ok) throw new Error("no manifest"); return r.json(); })
      .then(d => setAnimDefs(d.animations ?? []))
      .catch(() => {});
  }, [animBasePath]);

  // ── Set default tab ──────────────────────────────────────────────────
  useEffect(() => {
    if (tabInitialized) return;
    if (monster && !guide) {
      setActiveTab("stats");
      setTabInitialized(true);
    } else if (monster && guide) {
      setActiveTab("behavior");
      setTabInitialized(true);
    }
  }, [monster, guide, tabInitialized]);

  // ── Combo playback handler ─────────────────────────────────────────────
  const handlePlayCombo = useCallback((combo: Combo, index: number) => {
    if (!combo.from_animation_id && !combo.to_animation_id) return;

    // Build candidate animation IDs:
    // 1. Try the combined transition animation: {slug}-{to}-from-{from}
    // 2. Fall back to playing from + to as separate animations
    const candidates: string[] = [];

    if (combo.from_animation_id && combo.to_animation_id) {
      // Combined transition animation (e.g., "skeleton-footman-slash-from-stab")
      candidates.push(`${slug}-${combo.to_animation_id}-from-${combo.from_animation_id}`);
    }

    // Individual animations as fallback
    if (combo.from_animation_id) {
      candidates.push(`${slug}-${combo.from_animation_id}`);
    }
    if (combo.to_animation_id) {
      candidates.push(`${slug}-${combo.to_animation_id}`);
    }

    // Also try without slug prefix (original IDs)
    if (combo.from_animation_id) candidates.push(combo.from_animation_id);
    if (combo.to_animation_id) candidates.push(combo.to_animation_id);

    setPlayingComboIdx(index);
    setComboPlayback({
      animations: candidates,
      onComplete: () => setPlayingComboIdx(null),
    });
  }, [slug]);

  // ── Loading / Not Found ────────────────────────────────────────────────
  if (loading) {
    return (
      <div className={styles.page}>
        <div className={styles.loading}>Loading...</div>
      </div>
    );
  }

  if (!monster) {
    return (
      <div className={styles.page}>
        <div className={styles.notFound}>
          <h1 className={styles.notFoundTitle}>Monster Not Found</h1>
          <p className={styles.notFoundDesc}>
            Could not find a monster with slug &ldquo;{slug}&rdquo;.
          </p>
          <Link href="/monsters" className="btn btn-outline">Back to Monsters</Link>
        </div>
      </div>
    );
  }

  const gradeData = monster.grades[grade];
  const stats = gradeData?.stats ?? {};
  const availableGrades = Object.keys(monster.grades);
  const combos = gradeData?.combos ?? [];
  const abilities = gradeData?.abilities ?? [];

  // Build tab list — only show tabs that have content
  const tabs: { id: TabId; label: string }[] = [];
  if (guide) tabs.push({ id: "behavior", label: "Behavior" });
  if (guide) tabs.push({ id: "strategy", label: "Strategy" });
  tabs.push({ id: "stats", label: "Stats" });
  if (monster.attacks.length > 0) tabs.push({ id: "attacks", label: `Attacks (${monster.attacks.length})` });
  if (combos.length > 0) tabs.push({ id: "combos", label: `Combos (${combos.length})` });
  if ((monster.loot && monster.loot.length > 0) || monster.hunting_loot) tabs.push({ id: "loot", label: "Loot" });
  if (abilities.length > 0 && availableGrades.length > 1) tabs.push({ id: "abilities", label: `Abilities (${abilities.length})` });
  if (animDefs.length > 0) tabs.push({ id: "animations", label: `Animations (${animDefs.length})` });

  const classBadgeClass = CLASS_BADGE_STYLE[monster.class_type] ?? "classBadgeNormal";

  return (
    <div className={styles.page}>
      <div className={styles.pageInner}>
        {/* Breadcrumb */}
        <Link href="/monsters" className={styles.breadcrumb}>
          &larr; All Monsters
        </Link>

        {/* Two-Panel Split */}
        <div className={styles.splitLayout}>
          {/* ─── Left Panel: 3D Model ─── */}
          <div className={styles.modelPanel}>
            <div className={styles.modelContainer}>
              {hasModel ? (
                <ModelViewer
                  modelUrl={activeModelUrl}
                  animationsBasePath={animBasePath}
                  comboPlayback={comboPlayback}
                  animDefs={animDefs}
                  activeAnim={activeAnim}
                />
              ) : (
                <div className={styles.noModel}>No 3D model available</div>
              )}
            </div>
          </div>

          {/* ─── Right Panel: Content ─── */}
          <div className={styles.contentPanel}>
            {/* Header: Name */}
            <h1 className={styles.monsterName}>{monster.name}</h1>

            {/* Tags row: Class badge + creature types + dungeons */}
            <div className={styles.tagRow}>
              <span className={styles[classBadgeClass]}>
                {CLASS_LABELS[monster.class_type] ?? monster.class_type}
              </span>
              {monster.creature_types.map((t) => (
                <span key={t} className={styles.typeTag}>{t}</span>
              ))}
              {monster.dungeons.length > 0 && (
                <span className={styles.dungeonText}>
                  {monster.dungeons.join(", ")}
                </span>
              )}
            </div>

            {/* Controls row: Grade selector + key stats */}
            <div className={styles.controlsRow}>
              <div className={styles.gradeButtons}>
                {availableGrades.map((g) => {
                  const isActive = grade === g;
                  const color = GRADE_COLORS[g] ?? "var(--text-dim)";
                  return (
                    <button
                      key={g}
                      onClick={() => setGrade(g)}
                      className={isActive ? styles.gradeBtnActive : styles.gradeBtn}
                      style={isActive ? {
                        background: `color-mix(in srgb, ${color} 15%, transparent)`,
                        color: color,
                        borderColor: color,
                      } : undefined}
                    >
                      {g}
                    </button>
                  );
                })}
              </div>

              <div className={styles.controlsDivider} />

              <div className={styles.keyStats}>
                {KEY_STATS.map((key) => (
                  <span key={key} className={styles.keyStat}>
                    {KEY_STAT_LABELS[key]}{" "}
                    <span className={styles.keyStatValue}>{stats[key] ?? "—"}</span>
                  </span>
                ))}
                {gradeData && (
                  <span className={styles.keyStat}>
                    XP <span className={styles.keyStatValue}>{gradeData.exp_point}</span>
                  </span>
                )}
              </div>
            </div>

            {/* Divider */}
            <div className={styles.sectionDivider}>
              <div className={styles.dividerLine} />
              <div className={styles.dividerDiamond} />
              <div className={styles.dividerLine} />
            </div>

            {/* Tab Bar */}
            <div className={styles.tabBar}>
              {tabs.map((t) => (
                <button
                  key={t.id}
                  className={activeTab === t.id ? styles.tabActive : styles.tab}
                  onClick={() => setActiveTab(t.id)}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {/* Tab Content */}
            {activeTab === "behavior" && guide && (
              <BehaviorTab guide={guide} grade={grade} />
            )}

            {activeTab === "strategy" && guide && (
              <StrategyTab guide={guide} eliteDiffs={guide.elite_differences} grade={grade} />
            )}

            {activeTab === "stats" && (
              <StatsTab
                stats={stats}
                statusEffects={monster.status_effects}
                projectiles={monster.projectiles}
                aoe={monster.aoe}
                availableGrades={availableGrades}
                currentGrade={grade}
                monster={monster}
              />
            )}

            {activeTab === "attacks" && (
              <AttacksTab attacks={monster.attacks} baseDmg={stats.PhysicalDamageWeapon ?? 0} />
            )}

            {activeTab === "combos" && (
              <CombosTab
                combos={combos}
                playingIdx={playingComboIdx}
                onPlay={handlePlayCombo}
              />
            )}

            {activeTab === "loot" && (
              <LootTab loot={monster.loot ?? []} huntingLoot={monster.hunting_loot} />
            )}

            {activeTab === "abilities" && (
              <AbilitiesTab
                abilities={abilities}
                grade={grade}
                availableGrades={availableGrades}
                allGrades={monster.grades}
              />
            )}

            {activeTab === "animations" && (
              <AnimationsTab
                animDefs={animDefs}
                activeAnim={activeAnim}
                onSelect={(anim) => setActiveAnim(prev => prev?.id === anim.id ? null : anim)}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Stats
// ---------------------------------------------------------------------------

function StatsTab({
  stats, statusEffects, projectiles, aoe, availableGrades, currentGrade, monster,
}: {
  stats: Record<string, number>;
  statusEffects?: StatusEffect[];
  projectiles?: Projectile[];
  aoe?: AoeDef[];
  availableGrades: string[];
  currentGrade: string;
  monster: Monster;
}) {
  const hasAttrs = ATTRIBUTE_STATS.some((k) => stats[k] != null);
  const hasResistances = RESISTANCE_STATS.some((k) => stats[k] != null);

  return (
    <div>
      {/* Spawn Locations */}
      {monster.spawn_locations && monster.spawn_locations.length > 0 && (
        <>
          <h3 className={styles.sectionTitle}>Spawn Locations</h3>
          <div className={styles.spawnLocations}>
            {(() => {
              const grouped: Record<string, string[]> = {};
              for (const loc of monster.spawn_locations) {
                if (!grouped[loc.dungeon]) grouped[loc.dungeon] = [];
                grouped[loc.dungeon].push(loc.module);
              }
              return Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b)).map(([dungeon, modules]) => (
                <div key={dungeon} className={styles.spawnDungeon}>
                  <div className={styles.spawnDungeonName}>{dungeon}</div>
                  <div className={styles.spawnModules}>
                    {modules.sort().map((mod, i) => (
                      <span key={i} className={styles.spawnModule}>{mod}</span>
                    ))}
                  </div>
                </div>
              ));
            })()}
          </div>
        </>
      )}

      {/* Attributes */}
      {hasAttrs && (
        <>
          <h3 className={styles.sectionTitle}>Attributes</h3>
          <div className={styles.statsGrid}>
            {ATTRIBUTE_STATS.map((key) => {
              const val = stats[key];
              if (val == null) return null;
              return (
                <div key={key} className={styles.statRow}>
                  <span className={styles.statLabel}>{STAT_LABELS[key] ?? key}</span>
                  <span className={val === 0 ? styles.statValueZero : styles.statValue}>{val}</span>
                </div>
              );
            })}
          </div>
        </>
      )}

      {/* Resistances */}
      {hasResistances && (
        <>
          <h3 className={styles.sectionTitle}>Resistances</h3>
          <div className={styles.statsGrid}>
            {RESISTANCE_STATS.map((key) => {
              const val = stats[key];
              if (val == null) return null;
              return (
                <div key={key} className={styles.statRow}>
                  <span className={styles.statLabel}>{STAT_LABELS[key] ?? key}</span>
                  <span
                    className={val === 0 ? styles.statValueZero : styles.statValue}
                    style={val < 0 ? { color: "var(--red-300)" } : undefined}
                  >
                    {val}
                  </span>
                </div>
              );
            })}
          </div>
        </>
      )}

      {/* Status Effects */}
      {statusEffects && statusEffects.length > 0 && (
        <>
          <h3 className={styles.sectionTitle}>Status Effects ({statusEffects.length})</h3>
          <div className={styles.effectsGrid}>
            {statusEffects.map((eff, i) => (
              <div key={i} className={styles.effectCard}>
                {eff.icon && (
                  <img
                    src={`/icons/status/${eff.icon}.png`}
                    alt={eff.name}
                    width={28} height={28}
                    className={styles.effectIcon}
                  />
                )}
                <div>
                  <div className={styles.effectName}>{eff.name}</div>
                  {eff.tags.length > 0 && (
                    <div style={{ display: "flex", gap: "3px", flexWrap: "wrap", marginTop: "2px" }}>
                      {eff.tags.map((tag) => (
                        <span key={tag} className={styles.effectTag}>{tag}</span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Projectiles & AoE */}
      {((projectiles && projectiles.length > 0) || (aoe && aoe.length > 0)) && (
        <>
          <h3 className={styles.sectionTitle}>Projectiles & AoE</h3>
          <div className={styles.tagGroup}>
            {projectiles?.map((p, i) => (
              <div key={`p-${i}`} className={styles.projTag}>
                <span className={styles.projLabel}>Projectile</span>
                <span className={styles.tagName}>{p.name}</span>
              </div>
            ))}
            {aoe?.map((a, i) => (
              <div key={`a-${i}`} className={styles.projTag}>
                <span className={styles.aoeLabel}>AoE</span>
                <span className={styles.tagName}>{a.name}</span>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Grade Comparison */}
      {availableGrades.length > 1 && (
        <>
          <h3 className={styles.sectionTitle}>Grade Comparison</h3>
          <div className={styles.comparisonWrap}>
            <table className={styles.comparisonTable}>
              <thead>
                <tr>
                  <th style={{ textAlign: "left" }}>Stat</th>
                  {availableGrades.map((g) => (
                    <th
                      key={g}
                      style={{
                        textAlign: "right",
                        color: GRADE_COLORS[g] ?? "var(--text-bright)",
                      }}
                    >
                      {g}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[...KEY_STATS, ...ATTRIBUTE_STATS, ...RESISTANCE_STATS]
                  .filter((key) => availableGrades.some((g) => monster.grades[g]?.stats?.[key] != null))
                  .map((key) => (
                    <tr key={key}>
                      <td style={{ color: "var(--text-dim)" }}>{STAT_LABELS[key] ?? key}</td>
                      {availableGrades.map((g) => {
                        const val = monster.grades[g]?.stats?.[key];
                        return (
                          <td
                            key={g}
                            className={currentGrade === g ? styles.activeCol : undefined}
                            style={{
                              textAlign: "right",
                              color: val != null && val < 0 ? "var(--red-300)" : undefined,
                            }}
                          >
                            {val ?? "—"}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                <tr>
                  <td style={{ color: "var(--text-dim)" }}>XP</td>
                  {availableGrades.map((g) => (
                    <td
                      key={g}
                      className={currentGrade === g ? styles.activeCol : undefined}
                      style={{ textAlign: "right" }}
                    >
                      {monster.grades[g]?.exp_point ?? "—"}
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        </>
      )}

    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Attacks
// ---------------------------------------------------------------------------

function AttacksTab({ attacks, baseDmg }: { attacks: Attack[]; baseDmg: number }) {
  return (
    <div>
      {attacks.map((atk, i) => {
        const calcDmg = ((baseDmg * atk.damage_ratio) / 1000).toFixed(1);
        return (
          <div key={i} className={styles.attackRow}>
            <span className={styles.attackName}>{cleanAttackName(atk.name)}</span>
            <span className={styles.attackStat}>
              Ratio: <span className={styles.attackStatHighlight}>{(atk.damage_ratio / 10).toFixed(0)}%</span>
              {baseDmg > 0 && <span className={styles.attackStatDim}>({calcDmg} dmg)</span>}
            </span>
            <span className={styles.attackStat}>
              Impact: <span className={styles.attackStatBright}>{atk.impact_power}</span>
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Combos
// ---------------------------------------------------------------------------

function CombosTab({
  combos, playingIdx, onPlay,
}: {
  combos: Combo[];
  playingIdx: number | null;
  onPlay: (combo: Combo, index: number) => void;
}) {
  return (
    <div>
      {combos.map((combo, i) => {
        const isPlaying = playingIdx === i;
        const hasAnims = !!(combo.from_animation_id || combo.to_animation_id);
        return (
          <div
            key={i}
            className={isPlaying ? styles.comboRowPlaying : styles.comboRow}
            onClick={hasAnims ? () => onPlay(combo, i) : undefined}
            style={!hasAnims ? { cursor: "default" } : undefined}
          >
            {hasAnims && (
              <button
                className={styles.comboPlayBtn}
                onClick={(e) => { e.stopPropagation(); onPlay(combo, i); }}
                title="Play combo animation"
              >
                {isPlaying ? "■" : "▶"}
              </button>
            )}
            <span className={styles.comboFrom}>{combo.from}</span>
            <span className={styles.comboArrow}>→</span>
            <span className={styles.comboTo}>{combo.to}</span>
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Loot
// ---------------------------------------------------------------------------

function LootTab({ loot, huntingLoot }: { loot: LootDrop[]; huntingLoot?: HuntingLoot | null }) {
  return (
    <div>
      {loot.map((drop, i) => (
        <div key={i} className={styles.lootRow}>
          <span className={styles.lootName}>{drop.name}</span>
          <span className={styles.lootQty}>&times;{drop.quantity}</span>
        </div>
      ))}

      {huntingLoot && (
        <div
          className={styles.huntingLoot}
          style={{ borderColor: RARITY_COLORS[huntingLoot.rarity] ?? "var(--border-dim)" }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span
              className={styles.huntingLootRarity}
              style={{
                background: `color-mix(in srgb, ${RARITY_COLORS[huntingLoot.rarity] ?? "var(--text-dim)"} 15%, transparent)`,
                color: RARITY_COLORS[huntingLoot.rarity] ?? "var(--text-dim)",
              }}
            >
              {huntingLoot.rarity}
            </span>
            <span className={styles.huntingLootLabel}>Hunting Loot</span>
          </div>
          <div className={styles.huntingLootName}>{huntingLoot.name}</div>
          {huntingLoot.description && (
            <div className={styles.huntingLootDesc}>{huntingLoot.description}</div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Abilities
// ---------------------------------------------------------------------------

function AbilitiesTab({
  abilities, grade, availableGrades, allGrades,
}: {
  abilities: string[];
  grade: string;
  availableGrades: string[];
  allGrades: Record<string, MonsterGrade>;
}) {
  return (
    <div>
      <div className={styles.abilityPills}>
        {abilities.map((ability, i) => {
          const isExclusive = availableGrades
            .filter((g) => g !== grade)
            .every((g) => !allGrades[g]?.abilities?.includes(ability));
          return (
            <span key={i} className={isExclusive ? styles.abilityPillExclusive : styles.abilityPill}>
              {cleanAttackName(ability)}
            </span>
          );
        })}
      </div>
      {availableGrades.length > 1 && (
        <div className={styles.abilityHint}>
          Highlighted abilities are unique to this grade
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Behavior
// ---------------------------------------------------------------------------

function GradeBadge({ grades }: { grades?: string[] }) {
  if (!grades || grades.length === 0) return null;
  return (
    <span className={styles.gradeBadge} style={{
      color: grades.includes("Nightmare") ? "var(--red-300)" : "var(--gold-500)",
      borderColor: grades.includes("Nightmare") ? "var(--red-300)" : "var(--gold-500)",
    }}>
      {grades.join(" / ")} only
    </span>
  );
}

function AnimationsTab({
  animDefs, activeAnim, onSelect,
}: {
  animDefs: { id: string; label: string; file: string; loop: boolean }[];
  activeAnim: { id: string; label: string; file: string; loop: boolean } | null;
  onSelect: (anim: { id: string; label: string; file: string; loop: boolean }) => void;
}) {
  return (
    <div>
      <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: "12px" }}>
        Click an animation to play it in the 3D viewer. Click again to stop.
      </p>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
        {animDefs.map((anim) => {
          const isActive = activeAnim?.id === anim.id;
          return (
            <button key={anim.id} onClick={() => onSelect(anim)} style={{
              padding: "6px 14px", fontSize: "0.6875rem",
              fontFamily: "var(--font-heading)", letterSpacing: "0.06em",
              textTransform: "uppercase", cursor: "pointer",
              border: isActive ? "1px solid rgba(201,168,76,0.55)" : "1px solid rgba(201,168,76,0.18)",
              background: isActive ? "rgba(201,168,76,0.13)" : "rgba(201,168,76,0.04)",
              color: isActive ? "rgba(201,168,76,0.95)" : "rgba(201,168,76,0.45)",
              borderRadius: "2px", transition: "all 0.12s ease",
            }}>
              {isActive ? "■ " : "▶ "}{anim.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function BehaviorTab({ guide, grade }: { guide: GuideData; grade: string }) {
  // Filter phases visible for current grade
  const visiblePhases = guide.phases.filter(p => matchesGrade(p, grade));
  // Filter attack categories — filter both the category and individual attacks within
  const visibleCategories = guide.attack_categories
    .filter(cat => matchesGrade(cat, grade))
    .map(cat => ({
      ...cat,
      attacks: cat.attacks.filter(atk => matchesGrade(atk, grade)),
    }))
    .filter(cat => cat.attacks.length > 0);
  // Filter combo chains
  const visibleChains = guide.combo_flow.chains.filter(c => matchesGrade(c, grade));
  // Filter status effects
  const visibleEffects = guide.status_effects_detail.filter(e => matchesGrade(e, grade));

  return (
    <div>
      {/* Overview */}
      <p className={styles.guideOverview}>{guide.overview}</p>

      {/* Combat Phases */}
      <h3 className={styles.sectionTitle}>Combat Phases</h3>
      <div className={styles.phasesGrid}>
        {visiblePhases.map((phase, i) => (
          <div key={i} className={styles.phaseCard}>
            <div className={styles.phaseNumber}>{i + 1}</div>
            <div>
              <div className={styles.phaseName}>
                {phase.name}
                {isGradeExclusive(phase) && <GradeBadge grades={phase.grades} />}
              </div>
              <p className={styles.phaseDesc}>{phase.description}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Attack Tiers */}
      <h3 className={styles.sectionTitle}>Attack Damage Tiers</h3>
      {visibleCategories.map((cat) => (
        <div key={cat.tier} className={styles.tierSection}>
          <div className={styles.tierHeader}>
            <span className={styles.tierBadge} style={{ color: cat.color, borderColor: `${cat.color}44`, background: `${cat.color}12` }}>
              {cat.tier}
            </span>
            {isGradeExclusive(cat) && <GradeBadge grades={cat.grades} />}
          </div>
          {cat.attacks.map((atk, i) => {
            const ratioVal = atk.damage_ratio ?? atk.ratio ?? 0;
            const gradeDmg = grade === "Nightmare" && atk.damage_nightmare != null
              ? atk.damage_nightmare
              : grade === "Elite"
                ? atk.damage_elite
                : atk.damage_common;
            return (
              <div key={i} className={styles.tierAttackRow}>
                <div className={styles.tierAttackName}>
                  {atk.name}
                  {isGradeExclusive(atk) && <GradeBadge grades={atk.grades} />}
                </div>
                <div className={styles.tierAttackStats}>
                  <span className={styles.tierRatio} style={{ color: cat.color }}>{ratioVal / 10}%</span>
                  <span className={styles.tierDmg}>{gradeDmg} dmg</span>
                </div>
                <p className={styles.tierAttackNote}>{atk.note}</p>
              </div>
            );
          })}
        </div>
      ))}

      {/* Combo Flow */}
      <h3 className={styles.sectionTitle}>Combo Flow</h3>
      <p className={styles.guideSubtext}>{guide.combo_flow.description}</p>
      {visibleChains.length > 0 ? (
        <div className={styles.comboFlowGrid}>
          {visibleChains.map((chain, i) => (
            <div key={i} className={styles.comboFlowCard}>
              <div className={styles.comboFlowFrom}>
                {chain.from}
                {isGradeExclusive(chain) && <GradeBadge grades={chain.grades} />}
              </div>
              <div className={styles.comboFlowArrow}>→</div>
              <div className={styles.comboFlowTargets}>
                {chain.to.map((t, j) => (
                  <span key={j} className={styles.comboFlowTarget}>{t}</span>
                ))}
              </div>
              <p className={styles.comboFlowNote}>{chain.note}</p>
            </div>
          ))}
        </div>
      ) : (
        <p className={styles.guideSubtext} style={{ opacity: 0.5 }}>No combo chains for this grade.</p>
      )}

      {/* Status Effects Detail */}
      <h3 className={styles.sectionTitle}>Status Effects — Detailed</h3>
      {visibleEffects.map((eff, i) => (
        <div key={i} className={styles.effectDetailCard}>
          <div className={styles.effectDetailHeader}>
            <span className={styles.effectDetailName}>{eff.name}</span>
            {isGradeExclusive(eff) && <GradeBadge grades={eff.grades} />}
            <span className={styles.effectDetailType} data-type={eff.type}>{eff.type}</span>
            <span className={styles.effectDetailDuration}>{eff.duration}</span>
            {eff.stacks > 1 && <span className={styles.effectDetailStacks}>{eff.stacks} stacks max</span>}
          </div>
          <p className={styles.effectDetailDesc}>{eff.description}</p>
          <p className={styles.effectDetailCounter}>
            <span className={styles.counterLabel}>Counter:</span> {eff.counter}
          </p>
        </div>
      ))}

      {/* AI Perception */}
      <h3 className={styles.sectionTitle}>AI Perception</h3>
      <div className={styles.perceptionGrid}>
        {guide.ai_perception.sight_radius != null && (
          <div className={styles.perceptionItem}>
            <span className={styles.perceptionLabel}>Sight Range</span>
            <span className={styles.perceptionValue}>{guide.ai_perception.sight_radius}</span>
            <p className={styles.perceptionDesc}>{guide.ai_perception.sight_description}</p>
          </div>
        )}
        <div className={styles.perceptionItem}>
          <span className={styles.perceptionLabel}>Vision Angle</span>
          <span className={styles.perceptionValue}>{guide.ai_perception.vision_angle}°</span>
          <p className={styles.perceptionDesc}>{guide.ai_perception.vision_description}</p>
        </div>
        {guide.ai_perception.damage_sense && (
          <div className={styles.perceptionItem}>
            <span className={styles.perceptionLabel}>Damage Sense</span>
            <span className={styles.perceptionValue}>Active</span>
            <p className={styles.perceptionDesc}>{guide.ai_perception.damage_description}</p>
          </div>
        )}
        {guide.ai_perception.hearing && (
          <div className={styles.perceptionItem}>
            <span className={styles.perceptionLabel}>Hearing</span>
            <span className={styles.perceptionValue}>Active</span>
            <p className={styles.perceptionDesc}>{guide.ai_perception.hearing_description}</p>
          </div>
        )}
        {guide.ai_perception.stuck_tracking && (
          <div className={styles.perceptionItem}>
            <span className={styles.perceptionLabel}>Stuck Detection</span>
            <span className={styles.perceptionValue}>Active</span>
            <p className={styles.perceptionDesc}>{guide.ai_perception.stuck_description}</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Strategy
// ---------------------------------------------------------------------------

function StrategyTab({ guide, eliteDiffs, grade }: { guide: GuideData; eliteDiffs: string[]; grade: string }) {
  const priorityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
  const visibleStrategies = guide.strategies.filter(s => matchesGrade(s, grade));
  const sorted = [...visibleStrategies].sort(
    (a, b) => (priorityOrder[a.priority as keyof typeof priorityOrder] ?? 3) - (priorityOrder[b.priority as keyof typeof priorityOrder] ?? 3)
  );

  return (
    <div>
      <h3 className={styles.sectionTitle}>Combat Strategies</h3>
      {sorted.map((strat, i) => (
        <div key={i} className={styles.strategyCard} data-priority={strat.priority}>
          <div className={styles.strategyHeader}>
            <span className={styles.strategyPriority} data-priority={strat.priority}>
              {strat.priority}
            </span>
            <span className={styles.strategyTitle}>
              {strat.title}
              {isGradeExclusive(strat) && <GradeBadge grades={strat.grades} />}
            </span>
          </div>
          <p className={styles.strategyDesc}>{strat.description}</p>
        </div>
      ))}

      {/* Elite Differences */}
      <h3 className={styles.sectionTitle} style={{ marginTop: 28 }}>Grade Differences</h3>
      <div className={styles.eliteDiffList}>
        {eliteDiffs.map((diff, i) => (
          <div key={i} className={styles.eliteDiffItem}>
            <span className={styles.eliteDiffBullet} />
            {diff}
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function cleanAttackName(raw: string): string {
  let name = raw.replace(/^\d+\s*/, "");
  name = name.replace(/([a-z])([A-Z])/g, "$1 $2");
  name = name.replace(/([A-Z]+)([A-Z][a-z])/g, "$1 $2");
  return name;
}
