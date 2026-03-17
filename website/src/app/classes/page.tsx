"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import styles from "./classes.module.css";

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

interface GameClass {
  slug: string;
  name: string;
  flavor_text: string;
  role: string;
  base_stats: BaseStats;
  derived_stats: DerivedStats;
  perks: unknown[];
  skills: unknown[];
  spells: unknown[];
  usable_item_count: number;
}

interface ClassesDataRaw {
  version: string;
  generated_at: string;
  data: {
    classes: GameClass[];
  };
}

type SortKey = "name" | "health" | "strength" | "vigor" | "agility" | "dexterity" | "will" | "knowledge" | "resourcefulness";
type SortDir = "asc" | "desc";

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

const ROLE_CLASSES: Record<string, string> = {
  Melee: styles.roleMelee,
  Caster: styles.roleCaster,
  Hybrid: styles.roleHybrid,
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function truncate(text: string, max: number): string {
  if (text.length <= max) return text;
  return text.slice(0, max).replace(/\s+\S*$/, "") + "\u2026";
}

function getSortValue(cls: GameClass, key: SortKey): number | string {
  if (key === "name") return cls.name;
  if (key === "health") return cls.derived_stats.health;
  return cls.base_stats[key as keyof BaseStats];
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ClassesPage() {
  const router = useRouter();

  // Data state
  const [classes, setClasses] = useState<GameClass[] | null>(null);
  const [error, setError] = useState(false);

  // Filter state
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("All");

  // Sort state
  const [sortKey, setSortKey] = useState<SortKey>("name");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  // Mobile filter toggle
  const [showFilters, setShowFilters] = useState(false);

  // Fetch data
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

  useEffect(() => { loadData(); }, [loadData]);

  // Compute max stat value across all classes for bar normalization
  const maxStat = useMemo(() => {
    if (!classes) return 25;
    let max = 0;
    for (const cls of classes) {
      for (const key of STAT_KEYS) {
        if (cls.base_stats[key] > max) max = cls.base_stats[key];
      }
    }
    return max || 25;
  }, [classes]);

  // Filter + sort
  const filtered = useMemo(() => {
    if (!classes) return [];
    const q = search.toLowerCase();
    let list = classes.filter((cls) => {
      if (q && !cls.name.toLowerCase().includes(q)) return false;
      if (roleFilter !== "All" && cls.role !== roleFilter) return false;
      return true;
    });

    list.sort((a, b) => {
      const va = getSortValue(a, sortKey);
      const vb = getSortValue(b, sortKey);
      let cmp = 0;
      if (typeof va === "string" && typeof vb === "string") {
        cmp = va.localeCompare(vb);
      } else {
        cmp = (va as number) - (vb as number);
      }
      return sortDir === "asc" ? cmp : -cmp;
    });

    return list;
  }, [classes, search, roleFilter, sortKey, sortDir]);

  // Sort handler
  const handleSort = useCallback((key: SortKey) => {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortDir(key === "name" ? "asc" : "desc");
      setSortKey(key);
    }
  }, [sortKey]);

  // Sort arrow indicator
  const sortArrow = (key: SortKey) => {
    if (sortKey !== key) return null;
    return <span className={styles.sortArrow}>{sortDir === "asc" ? "\u25B2" : "\u25BC"}</span>;
  };

  // -- Loading state --
  if (!classes && !error) {
    return (
      <div className={styles.page}>
        <div className={`container ${styles.pageInner}`}>
          <div className="section-head">
            <span className="section-label">Roster</span>
            <h1 className="section-title">Classes</h1>
          </div>
          <div className={styles.cardGrid}>
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className={styles.skeletonCard}>
                <div className={styles.skeletonHeader}>
                  <div className={styles.skeletonBar} style={{ width: "50%", height: 18 }} />
                  <div className={styles.skeletonBar} style={{ width: 60, height: 18 }} />
                </div>
                <div className={styles.skeletonBar} style={{ width: "90%", height: 12, marginBottom: 8 }} />
                <div className={styles.skeletonBar} style={{ width: "70%", height: 12, marginBottom: 20 }} />
                {Array.from({ length: 7 }).map((_, j) => (
                  <div key={j} className={styles.skeletonStatRow}>
                    <div className={styles.skeletonBar} style={{ width: 70, height: 8 }} />
                    <div className={styles.skeletonBar} style={{ flex: 1, height: 6 }} />
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // -- Error state --
  if (error) {
    return (
      <div className={styles.page}>
        <div className={`container ${styles.pageInner}`}>
          <div className="section-head">
            <span className="section-label">Roster</span>
            <h1 className="section-title">Classes</h1>
          </div>
          <div className={styles.errorState}>
            <p className={styles.errorText}>Failed to load class data</p>
            <button className={styles.retryButton} onClick={loadData}>Retry</button>
          </div>
        </div>
      </div>
    );
  }

  // -- Main render --
  return (
    <div className={styles.page}>
      <div className={`container ${styles.pageInner}`}>
        {/* Header */}
        <div className="section-head" style={{ marginBottom: "36px" }}>
          <span className="section-label">Roster</span>
          <h1 className="section-title">Classes</h1>
          <p className="section-desc">
            All {filtered.length} adventurer classes with base stats, perks, and skills.
          </p>
          <div className={styles.headerDivider} />
        </div>

        {/* Filter Bar */}
        <div className={styles.filterBar}>
          <input
            type="text"
            placeholder="Search classes..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className={styles.searchInput}
          />
          <button
            className={styles.mobileFilterToggle}
            onClick={() => setShowFilters((v) => !v)}
          >
            Filters {showFilters ? "\u25B2" : "\u25BC"}
          </button>
          <div className={showFilters ? undefined : styles.mobileFiltersHidden}>
            <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)} className={styles.filterSelect}>
              <option value="All">All Roles</option>
              <option value="Melee">Melee</option>
              <option value="Caster">Caster</option>
              <option value="Hybrid">Hybrid</option>
            </select>
          </div>
        </div>

        {/* Sort Controls */}
        <div className={styles.sortBar}>
          {(
            [
              ["name", "Name"],
              ["health", "Health"],
              ["strength", "STR"],
              ["vigor", "VIG"],
              ["agility", "AGI"],
              ["dexterity", "DEX"],
              ["will", "WIL"],
              ["knowledge", "KNO"],
              ["resourcefulness", "RES"],
            ] as [SortKey, string][]
          ).map(([key, label]) => (
            <button
              key={key}
              className={`${styles.sortButton} ${sortKey === key ? styles.sortButtonActive : ""}`}
              onClick={() => handleSort(key)}
            >
              {label}{sortArrow(key)}
            </button>
          ))}
        </div>

        {/* Result count */}
        <p className={styles.resultCount}>
          {filtered.length} class{filtered.length !== 1 ? "es" : ""}
        </p>

        {/* Card Grid */}
        <div className={styles.cardGrid}>
          {filtered.length === 0 ? (
            <div className={styles.emptyState}>No classes match your search</div>
          ) : (
            filtered.map((cls, i) => (
              <div
                key={cls.slug}
                className={`${styles.classCard} ${i < 20 ? styles.cardAnimated : ""}`}
                style={i < 20 ? { animationDelay: `${i * 60}ms` } : undefined}
                onClick={() => router.push(`/classes/${cls.slug}`)}
              >
                {/* Card Header */}
                <div className={styles.cardHeader}>
                  <Link
                    href={`/classes/${cls.slug}`}
                    className={styles.className}
                    onClick={(e) => e.stopPropagation()}
                  >
                    {cls.name}
                  </Link>
                  <span className={`${styles.roleBadge} ${ROLE_CLASSES[cls.role] ?? ""}`}>
                    {cls.role}
                  </span>
                </div>

                {/* Flavor Text */}
                <p className={styles.flavorText}>
                  {truncate(cls.flavor_text, 120)}
                </p>

                {/* Stat Bars */}
                <div className={styles.statsContainer}>
                  {STAT_KEYS.map((statKey) => {
                    const value = cls.base_stats[statKey];
                    const pct = Math.round((value / maxStat) * 100);
                    return (
                      <div key={statKey} className={styles.statRow}>
                        <span className={styles.statLabel}>{STAT_LABELS[statKey]}</span>
                        <div className={styles.statBarTrack}>
                          <div
                            className={styles.statBarFill}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <span className={styles.statValue}>{value}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
