"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import styles from "./monsters.module.css";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface MonsterGrade {
  adv_point: number;
  exp_point: number;
  stats: Record<string, number>;
}

interface Monster {
  slug: string;
  name: string;
  class_type: string;
  creature_types: string[];
  image: string;
  dungeons: string[];
  grades: Record<string, MonsterGrade>;
  attacks: { name: string; damage_ratio: number; impact_power: number }[];
}

interface MonstersData {
  generated_at: string;
  monsters: Monster[];
}

type SortKey = "name" | "hp" | "dmg" | "speed";
type SortDir = "asc" | "desc";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const ALL_DUNGEONS = [
  "Goblin Cave", "Crypt", "Ruins", "Ice Cavern",
  "Ice Abyss", "Inferno", "Firedeep", "Ship Graveyard",
];

const CLASS_LABELS: Record<string, string> = {
  Normal: "Normal",
  SubBoss: "Sub-Boss",
  Boss: "Boss",
};

const BADGE_CLASS: Record<string, string> = {
  Normal: styles.classBadgeNormal,
  SubBoss: styles.classBadgeSubBoss,
  Boss: styles.classBadgeBoss,
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getStats(monster: Monster) {
  const grade = monster.grades.Common ?? Object.values(monster.grades)[0];
  const s = grade?.stats ?? {};
  return {
    hp: s.MaxHealthAdd ?? 0,
    dmg: s.PhysicalDamageWeapon ?? 0,
    speed: s.MoveSpeedBase ?? 0,
  };
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function MonstersPage() {
  const router = useRouter();

  // Data state
  const [data, setData] = useState<MonstersData | null>(null);
  const [error, setError] = useState(false);

  // Filter state
  const [search, setSearch] = useState("");
  const [classFilter, setClassFilter] = useState("All");
  const [typeFilter, setTypeFilter] = useState("All");
  const [dungeonFilter, setDungeonFilter] = useState("All");

  // Sort state
  const [sortKey, setSortKey] = useState<SortKey>("name");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  // Mobile filter toggle
  const [showFilters, setShowFilters] = useState(false);

  // Fetch data
  useEffect(() => {
    fetch("/data/monsters.json")
      .then((r) => {
        if (!r.ok) throw new Error("fetch failed");
        return r.json();
      })
      .then(setData)
      .catch(() => setError(true));
  }, []);

  const retry = useCallback(() => {
    setError(false);
    setData(null);
    fetch("/data/monsters.json")
      .then((r) => {
        if (!r.ok) throw new Error("fetch failed");
        return r.json();
      })
      .then(setData)
      .catch(() => setError(true));
  }, []);

  // All types for filter dropdown
  const allTypes = useMemo(() => {
    if (!data) return [];
    const s = new Set<string>();
    data.monsters.forEach((m) => m.creature_types.forEach((t) => s.add(t)));
    return Array.from(s).sort();
  }, [data]);

  // Filter + sort
  const filtered = useMemo(() => {
    if (!data) return [];
    const q = search.toLowerCase();
    let list = data.monsters.filter((m) => {
      if (q && !m.name.toLowerCase().includes(q)) return false;
      if (classFilter !== "All" && m.class_type !== classFilter) return false;
      if (typeFilter !== "All" && !m.creature_types.includes(typeFilter)) return false;
      if (dungeonFilter !== "All" && !m.dungeons.includes(dungeonFilter)) return false;
      return true;
    });

    list.sort((a, b) => {
      const sa = getStats(a);
      const sb = getStats(b);
      let cmp = 0;
      switch (sortKey) {
        case "name": cmp = a.name.localeCompare(b.name); break;
        case "hp": cmp = sa.hp - sb.hp; break;
        case "dmg": cmp = sa.dmg - sb.dmg; break;
        case "speed": cmp = sa.speed - sb.speed; break;
      }
      return sortDir === "asc" ? cmp : -cmp;
    });

    return list;
  }, [data, search, classFilter, typeFilter, dungeonFilter, sortKey, sortDir]);

  // Sort handler
  const handleSort = useCallback((key: SortKey) => {
    setSortKey((prev) => {
      if (prev === key) {
        setSortDir((d) => (d === "asc" ? "desc" : "asc"));
      } else {
        setSortDir(key === "name" ? "asc" : "desc");
      }
      return key;
    });
  }, []);

  // Sort arrow indicator
  const sortArrow = (key: SortKey) => {
    if (sortKey !== key) return null;
    return <span className={styles.sortArrow}>{sortDir === "asc" ? "\u25B2" : "\u25BC"}</span>;
  };

  // Header cell helper
  const hCell = (label: string, key?: SortKey, center?: boolean) => {
    const base = center ? styles.headerCellCenter : styles.headerCell;
    if (!key) return <div className={base}>{label}</div>;
    const classes = [
      base,
      styles.headerCellSortable,
      sortKey === key ? styles.headerCellActive : "",
    ].filter(Boolean).join(" ");
    return (
      <div className={classes} onClick={() => handleSort(key)}>
        {label}{sortArrow(key)}
      </div>
    );
  };

  // -- Loading state --
  if (!data && !error) {
    return (
      <div className={styles.page}>
        <div className={`container ${styles.pageInner}`}>
          <div className="section-head">
            <span className="section-label">Bestiary</span>
            <h1 className="section-title">Monsters</h1>
          </div>
          <div className={styles.tableContainer}>
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className={styles.skeletonRow}>
                <div className={styles.cell}><div className={styles.skeletonCircle} /></div>
                <div className={styles.cell}><div className={styles.skeletonBar} style={{ width: "60%" }} /></div>
                <div className={styles.cellCenter}><div className={styles.skeletonBar} style={{ width: "50%", margin: "0 auto" }} /></div>
                <div className={styles.cellCenter}><div className={styles.skeletonBar} style={{ width: "40%", margin: "0 auto" }} /></div>
                <div className={styles.cellCenter}><div className={styles.skeletonBar} style={{ width: "30%", margin: "0 auto" }} /></div>
                <div className={styles.cellCenter}><div className={styles.skeletonBar} style={{ width: "30%", margin: "0 auto" }} /></div>
                <div className={`${styles.cellCenter} ${styles.colSpeed}`}><div className={styles.skeletonBar} style={{ width: "30%", margin: "0 auto" }} /></div>
                <div className={`${styles.cellCenter} ${styles.colAttacks}`}><div className={styles.skeletonBar} style={{ width: "30%", margin: "0 auto" }} /></div>
                <div className={styles.cell}><div className={styles.skeletonBar} style={{ width: "70%" }} /></div>
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
            <span className="section-label">Bestiary</span>
            <h1 className="section-title">Monsters</h1>
          </div>
          <div className={styles.errorState}>
            <p className={styles.errorText}>Failed to load bestiary data</p>
            <button className={styles.retryButton} onClick={retry}>Retry</button>
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
          <span className="section-label">Bestiary</span>
          <h1 className="section-title">Monsters</h1>
          <p className="section-desc">
            {data!.monsters.length} creatures with stats, attacks, and spawn locations.
          </p>
          <div className={styles.headerDivider} />
        </div>

        {/* Filter Bar */}
        <div className={styles.filterBar}>
          <input
            type="text"
            placeholder="Search monsters..."
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
            <select value={classFilter} onChange={(e) => setClassFilter(e.target.value)} className={styles.filterSelect}>
              <option value="All">All Classes</option>
              <option value="Normal">Normal</option>
              <option value="SubBoss">Sub-Boss</option>
              <option value="Boss">Boss</option>
            </select>
          </div>
          <div className={showFilters ? undefined : styles.mobileFiltersHidden}>
            <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} className={styles.filterSelect}>
              <option value="All">All Types</option>
              {allTypes.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div className={showFilters ? undefined : styles.mobileFiltersHidden}>
            <select value={dungeonFilter} onChange={(e) => setDungeonFilter(e.target.value)} className={styles.filterSelect}>
              <option value="All">All Dungeons</option>
              {ALL_DUNGEONS.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
        </div>

        {/* Result count */}
        <p className={styles.resultCount}>
          {filtered.length} monster{filtered.length !== 1 ? "s" : ""}
        </p>

        {/* Table */}
        <div className={styles.tableContainer}>
          {/* Header row */}
          <div className={styles.headerRow}>
            <div className={styles.headerCell} />
            {hCell("Name", "name")}
            {hCell("Class", undefined, true)}
            {hCell("Type", undefined, true)}
            {hCell("HP", "hp", true)}
            {hCell("DMG", "dmg", true)}
            <div className={`${styles.headerCellCenter} ${styles.colSpeed} ${styles.headerCellSortable} ${sortKey === "speed" ? styles.headerCellActive : ""}`}
              onClick={() => handleSort("speed")}>
              Spd{sortArrow("speed")}
            </div>
            <div className={`${styles.headerCellCenter} ${styles.colAttacks}`}>Atk</div>
            {hCell("Dungeon")}
          </div>

          {/* Data rows */}
          {filtered.length === 0 ? (
            <div className={styles.emptyState}>No creatures match your search</div>
          ) : (
            filtered.map((m, i) => {
              const { hp, dmg, speed } = getStats(m);
              return (
                <div
                  key={m.slug}
                  className={`${styles.dataRow} ${i < 20 ? styles.rowAnimated : ""}`}
                  style={i < 20 ? { animationDelay: `${i * 30}ms` } : undefined}
                  onClick={() => router.push(`/monsters/${m.slug}`)}
                >
                  <div className={`${styles.cell} ${styles.colPortrait}`}>
                    <div className={styles.portrait} />
                  </div>
                  <div className={`${styles.cell} ${styles.colName}`}>
                    <Link href={`/monsters/${m.slug}`} className={styles.monsterName} onClick={(e) => e.stopPropagation()}>
                      {m.name}
                    </Link>
                  </div>
                  <div className={`${styles.cellCenter} ${styles.colClass}`}>
                    <span className={BADGE_CLASS[m.class_type] ?? styles.classBadgeNormal}>
                      {CLASS_LABELS[m.class_type] ?? m.class_type}
                    </span>
                  </div>
                  <div className={`${styles.cellCenter} ${styles.colType}`}>
                    <span className={styles.typeText}>{m.creature_types.join(", ") || "\u2014"}</span>
                  </div>
                  <div className={`${styles.cellCenter} ${styles.colHp}`}>
                    <span className={hp > 0 ? styles.statValue : styles.statEmpty}>{hp > 0 ? hp : "\u2014"}</span>
                  </div>
                  <div className={`${styles.cellCenter} ${styles.colDmg}`}>
                    <span className={dmg > 0 ? styles.statValue : styles.statEmpty}>{dmg > 0 ? dmg : "\u2014"}</span>
                  </div>
                  <div className={`${styles.cellCenter} ${styles.colSpeed}`}>
                    <span className={speed > 0 ? styles.statValue : styles.statEmpty}>{speed > 0 ? speed : "\u2014"}</span>
                  </div>
                  <div className={`${styles.cellCenter} ${styles.colAttacks}`}>
                    <span className={styles.attackCount}>{m.attacks.length || "\u2014"}</span>
                  </div>
                  <div className={`${styles.cell} ${styles.colDungeon}`}>
                    <span className={styles.dungeonText}>
                      {m.dungeons.length > 0 ? m.dungeons.join(", ") : "\u2014"}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
