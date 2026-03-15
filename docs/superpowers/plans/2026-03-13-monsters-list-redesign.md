# Monsters List Page Redesign — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the `/monsters` page from a raw table to a polished, visually rich grid-based table matching the home page's dark medieval design system.

**Architecture:** Replace the current `<table>` markup with a CSS Grid div-based layout for responsive flexibility. Extract all styles into a CSS module (`monsters.module.css`). Keep the existing client-side data fetching and filtering logic, adding sort and visual polish.

**Tech Stack:** Next.js 14 (App Router), React, CSS Modules, TypeScript

**Spec:** `docs/superpowers/specs/2026-03-13-monsters-list-redesign.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `website/src/app/monsters/monsters.module.css` | Create | All page-specific styles: header, filters, grid table, rows, badges, responsive breakpoints, animations |
| `website/src/app/monsters/page.tsx` | Rewrite | Page component: header, filters, sort state, grid-based monster list, loading/error/empty states |

No data pipeline changes — same `monsters.json` schema.

**Key design system references (all in `website/src/app/globals.css`):**
- CSS variables: `--bg-deep`, `--bg-raised`, `--bg-card`, `--bg-card-h`, `--border-dim`, `--gold-*`, `--text-*`, `--font-*`
- Classes: `.container`, `.section-head`, `.section-label`, `.section-title`, `.section-desc`, `.stub-page`
- Keyframes: `fade-in-up` (already defined globally)
- Corner ornament pattern: `.tool-card::before/::after` (replicate in module)

---

## Chunk 1: CSS Module + Page Scaffold

### Task 1: Create the CSS module

**Files:**
- Create: `website/src/app/monsters/monsters.module.css`

- [ ] **Step 1: Create `monsters.module.css` with page layout, header, filter bar styles**

```css
/* === Page Layout === */

.page {
  min-height: 100vh;
  padding-top: var(--nav-h);
  background: var(--bg-deep);
}

.pageInner {
  padding-block: 48px;
}

/* === Header === */

.header {
  text-align: center;
  margin-bottom: 40px;
}

.headerDivider {
  width: 60px;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--gold-700), transparent);
  margin: 20px auto 0;
}

/* === Filter Bar === */

.filterBar {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 24px;
  justify-content: center;
}

.searchInput {
  flex: 1 1 220px;
  max-width: 320px;
  padding: 9px 14px;
  background: var(--bg-raised);
  border: 1px solid var(--border-dim);
  border-radius: 2px;
  color: var(--text-bright);
  font-family: var(--font-body);
  font-size: 0.8125rem;
  outline: none;
  transition: border-color var(--t-fast), box-shadow var(--t-fast);
}

.searchInput::placeholder {
  color: var(--text-muted);
}

.searchInput:focus {
  border-color: var(--gold-600);
  box-shadow: 0 0 0 1px var(--gold-800);
}

.filterSelect {
  padding: 9px 14px;
  background: var(--bg-raised);
  border: 1px solid var(--border-dim);
  border-radius: 2px;
  color: var(--text-bright);
  font-family: var(--font-body);
  font-size: 0.8125rem;
  cursor: pointer;
  outline: none;
  transition: border-color var(--t-fast);
}

.filterSelect:focus {
  border-color: var(--gold-600);
}

.resultCount {
  text-align: center;
  color: var(--text-muted);
  font-size: 0.6875rem;
  letter-spacing: 0.1em;
  margin-bottom: 20px;
  font-family: var(--font-heading);
  text-transform: uppercase;
}
```

- [ ] **Step 2: Add table container and corner ornament styles**

Append to `monsters.module.css`:

```css
/* === Table Container === */

.tableContainer {
  position: relative;
  border: 1px solid var(--border-dim);
  border-radius: 2px;
  background: var(--bg-card);
  overflow: hidden;
}

/* Corner ornaments — same pattern as .tool-card in globals.css */
.tableContainer::before,
.tableContainer::after {
  content: '';
  position: absolute;
  width: 18px;
  height: 18px;
  opacity: 0.4;
  z-index: 1;
  pointer-events: none;
}

.tableContainer::before {
  top: 10px;
  left: 10px;
  border-top: 1.5px solid var(--gold-500);
  border-left: 1.5px solid var(--gold-500);
}

.tableContainer::after {
  bottom: 10px;
  right: 10px;
  border-bottom: 1.5px solid var(--gold-500);
  border-right: 1.5px solid var(--gold-500);
}
```

- [ ] **Step 3: Add grid header row and data row styles**

Append to `monsters.module.css`:

```css
/* === Grid Layout === */

.gridRow {
  display: grid;
  grid-template-columns: 40px 1fr 80px 90px 60px 60px 60px 60px auto;
  align-items: center;
  padding: 0 12px;
}

/* Header row */
.headerRow {
  composes: gridRow;
  background: var(--bg-raised);
  border-bottom: 1px solid var(--border-dim);
}

.headerCell {
  padding: 10px 8px;
  font-family: var(--font-heading);
  font-size: 0.625rem;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--text-muted);
  white-space: nowrap;
  user-select: none;
}

.headerCellCenter {
  composes: headerCell;
  text-align: center;
}

.headerCellSortable {
  cursor: pointer;
  transition: color var(--t-fast);
}

.headerCellSortable:hover {
  color: var(--text-dim);
}

.headerCellActive {
  color: var(--gold-700);
}

.sortArrow {
  margin-left: 4px;
  font-size: 0.5rem;
  opacity: 0.7;
}

/* Data rows */
.dataRow {
  composes: gridRow;
  border-bottom: 1px solid rgba(201, 168, 76, 0.06);
  cursor: pointer;
  transition: background var(--t-fast);
  text-decoration: none;
  color: inherit;
}

.dataRow:nth-child(even) {
  background: rgba(201, 168, 76, 0.015);
}

.dataRow:hover {
  background: var(--bg-card-h);
  box-shadow: inset 3px 0 0 rgba(201, 168, 76, 0.4);
}

.dataRow:active {
  background: rgba(201, 168, 76, 0.08);
}

.cell {
  padding: 10px 8px;
}

.cellCenter {
  composes: cell;
  text-align: center;
}
```

- [ ] **Step 4: Add portrait, name, badge, stat, and dungeon styles**

Append to `monsters.module.css`:

```css
/* === Row Content Styles === */

.portrait {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: radial-gradient(circle, #2a2418, #151210);
  border: 1px solid rgba(201, 168, 76, 0.1);
  flex-shrink: 0;
}

.monsterName {
  font-family: var(--font-heading);
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--gold-300);
  letter-spacing: 0.04em;
  text-decoration: none;
  transition: color var(--t-fast);
}

.dataRow:hover .monsterName {
  color: var(--gold-100);
}

.classBadge {
  display: inline-block;
  font-size: 0.625rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 2px 8px;
  border-radius: 1px;
  font-family: var(--font-heading);
  white-space: nowrap;
}

.classBadgeNormal {
  composes: classBadge;
  background: var(--bg-raised);
  border: 1px solid var(--border-dim);
  color: var(--text-dim);
}

.classBadgeBoss {
  composes: classBadge;
  background: var(--red-900);
  border: 1px solid var(--red-700);
  color: var(--red-300);
}

.classBadgeSubBoss {
  composes: classBadge;
  background: var(--gold-950);
  border: 1px solid var(--gold-800);
  color: var(--gold-500);
}

.typeText {
  font-size: 0.75rem;
  color: var(--text-dim);
}

.statValue {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--text-bright);
}

.statEmpty {
  font-size: 0.8125rem;
  color: var(--text-muted);
}

.attackCount {
  color: var(--text-dim);
}

.dungeonText {
  font-size: 0.75rem;
  color: var(--text-dim);
}
```

- [ ] **Step 5: Add loading skeleton, error, empty, and animation styles**

Append to `monsters.module.css`:

```css
/* === States === */

.emptyState {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-muted);
  font-family: var(--font-heading);
  font-size: 0.875rem;
  letter-spacing: 0.06em;
}

.errorState {
  text-align: center;
  padding: 60px 20px;
}

.errorText {
  color: var(--text-muted);
  font-family: var(--font-heading);
  font-size: 0.875rem;
  letter-spacing: 0.06em;
  margin-bottom: 16px;
}

.retryButton {
  padding: 8px 20px;
  background: var(--bg-raised);
  border: 1px solid var(--border-dim);
  border-radius: 2px;
  color: var(--gold-500);
  font-family: var(--font-heading);
  font-size: 0.75rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  cursor: pointer;
  transition: border-color var(--t-fast), color var(--t-fast);
}

.retryButton:hover {
  border-color: var(--gold-600);
  color: var(--gold-300);
}

/* Skeleton loading */
.skeletonRow {
  composes: gridRow;
  border-bottom: 1px solid rgba(201, 168, 76, 0.06);
  padding-top: 10px;
  padding-bottom: 10px;
}

.skeletonBar {
  height: 12px;
  border-radius: 2px;
  background: linear-gradient(90deg, var(--bg-raised) 25%, var(--bg-card-h) 50%, var(--bg-raised) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

.skeletonCircle {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: linear-gradient(90deg, var(--bg-raised) 25%, var(--bg-card-h) 50%, var(--bg-raised) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* Row entrance animation */
.rowAnimated {
  animation: fade-in-up 0.4s var(--ease) both;
}
```

- [ ] **Step 6: Add responsive breakpoint styles**

Append to `monsters.module.css`:

```css
/* === Responsive === */

/* Tablet: hide Speed and Attacks columns */
@media (max-width: 1024px) {
  .gridRow {
    /* Portrait | Name | Class | Type | HP | DMG | Dungeon */
    grid-template-columns: 40px 1fr 80px 80px 50px 50px auto;
  }

  .colSpeed,
  .colAttacks {
    display: none;
  }

  .cell,
  .headerCell,
  .headerCellCenter,
  .cellCenter {
    padding: 8px 6px;
  }
}

/* Mobile: card list layout */
@media (max-width: 768px) {
  .filterBar {
    flex-direction: column;
    align-items: stretch;
  }

  .searchInput {
    max-width: none;
  }

  .mobileFilterToggle {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 9px 14px;
    background: var(--bg-raised);
    border: 1px solid var(--border-dim);
    border-radius: 2px;
    color: var(--text-dim);
    font-family: var(--font-heading);
    font-size: 0.75rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    cursor: pointer;
  }

  .mobileFiltersHidden {
    display: none;
  }

  .headerRow {
    display: none;
  }

  .gridRow {
    grid-template-columns: 36px 1fr auto;
    grid-template-rows: auto auto;
    gap: 0 10px;
    padding: 10px 12px;
  }

  .dataRow {
    border-bottom: 1px solid rgba(201, 168, 76, 0.06);
  }

  /* Portrait spans both rows */
  .colPortrait {
    grid-row: 1 / 3;
    align-self: center;
  }

  /* Name + class on first row */
  .colName {
    grid-column: 2;
    grid-row: 1;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .colClass {
    grid-column: 3;
    grid-row: 1;
  }

  /* HP below name */
  .colHp {
    grid-column: 2 / 4;
    grid-row: 2;
    text-align: left;
    font-size: 0.6875rem;
  }

  .colHp::before {
    content: 'HP ';
    color: var(--text-muted);
    font-family: var(--font-heading);
    font-size: 0.5625rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  /* Hide these on mobile */
  .colType,
  .colDmg,
  .colSpeed,
  .colAttacks,
  .colDungeon {
    display: none;
  }
}

/* Desktop: show all, hide mobile toggle */
@media (min-width: 769px) {
  .mobileFilterToggle {
    display: none;
  }
}
```

- [ ] **Step 7: Verify CSS module compiles**

Run: `cd C:/Users/Administrator/Desktop/DnDMainProject/darkanddarker-wiki/website && npx next build --no-lint 2>&1 | head -30`

Expected: No CSS compilation errors. Build may warn about other things but CSS module should parse successfully.

- [ ] **Step 8: Commit CSS module**

```bash
cd C:/Users/Administrator/Desktop/DnDMainProject/darkanddarker-wiki
git add website/src/app/monsters/monsters.module.css
git commit -m "feat(monsters): add CSS module with polished table styles

Styles for the redesigned monsters list page: grid-based table layout,
corner ornaments, class badges, sort indicators, skeleton loading,
fade-in animations, and responsive breakpoints (tablet + mobile)."
```

---

### Task 2: Rewrite page.tsx — page header + filter bar + grid table

**Files:**
- Modify: `website/src/app/monsters/page.tsx` (full rewrite)

- [ ] **Step 1: Write the complete new `page.tsx`**

Replace the entire file with:

```tsx
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
    return <span className={styles.sortArrow}>{sortDir === "asc" ? "▲" : "▼"}</span>;
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

  // ── Loading state ──
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

  // ── Error state ──
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

  // ── Main render ──
  return (
    <div className={styles.page}>
      <div className={`container ${styles.pageInner}`}>
        {/* Header */}
        <div className="section-head" style={{ marginBottom: "36px" }}>
          <span className="section-label">Bestiary</span>
          <h1 className="section-title">Monsters</h1>
          <p className="section-desc">
            {data.monsters.length} creatures with stats, attacks, and spawn locations.
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
            Filters {showFilters ? "▲" : "▼"}
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
                    <span className={styles.typeText}>{m.creature_types.join(", ") || "—"}</span>
                  </div>
                  <div className={`${styles.cellCenter} ${styles.colHp}`}>
                    <span className={hp > 0 ? styles.statValue : styles.statEmpty}>{hp > 0 ? hp : "—"}</span>
                  </div>
                  <div className={`${styles.cellCenter} ${styles.colDmg}`}>
                    <span className={dmg > 0 ? styles.statValue : styles.statEmpty}>{dmg > 0 ? dmg : "—"}</span>
                  </div>
                  <div className={`${styles.cellCenter} ${styles.colSpeed}`}>
                    <span className={speed > 0 ? styles.statValue : styles.statEmpty}>{speed > 0 ? speed : "—"}</span>
                  </div>
                  <div className={`${styles.cellCenter} ${styles.colAttacks}`}>
                    <span className={styles.attackCount}>{m.attacks.length || "—"}</span>
                  </div>
                  <div className={`${styles.cell} ${styles.colDungeon}`}>
                    <span className={styles.dungeonText}>
                      {m.dungeons.length > 0 ? m.dungeons.join(", ") : "—"}
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
```

- [ ] **Step 2: Verify the page renders**

Run: `cd C:/Users/Administrator/Desktop/DnDMainProject/darkanddarker-wiki/website && npx next build --no-lint 2>&1 | tail -20`

Expected: Build succeeds. No TypeScript or CSS errors.

- [ ] **Step 3: Visual verification in browser**

Open `http://localhost:3000/monsters` in browser. Verify:
1. Page header shows "Bestiary" / "Monsters" with gold divider
2. Filter bar has search + 3 dropdowns + count
3. Table shows grid rows with portrait circles, gold names, class badges
4. Rows have alternating tints and hover glow with left gold accent
5. Clicking a row navigates to the monster detail page
6. Sort by clicking Name/HP/DMG/Spd column headers
7. Corner ornaments visible on table container
8. First 20 rows fade in with staggered animation
9. Skeleton loading shows briefly on page load

- [ ] **Step 4: Test responsive behavior**

In browser dev tools:
1. At 900px width: Speed and Attacks columns should be hidden
2. At 600px width: Card-list layout with portrait, name+badge, HP
3. Search stays full-width on mobile
4. "Filters" toggle button appears and hides/shows dropdowns

- [ ] **Step 5: Commit page rewrite**

```bash
cd C:/Users/Administrator/Desktop/DnDMainProject/darkanddarker-wiki
git add website/src/app/monsters/page.tsx
git commit -m "feat(monsters): redesign list page with polished table

Replaces raw HTML table with CSS Grid layout, adds:
- Page header with Bestiary title and gold divider
- Sortable columns (Name, HP, DMG, Speed)
- Portrait circles, styled class badges, hover glows
- Corner ornaments on table container
- Skeleton loading, error state with retry, empty state
- Staggered fade-in animation on first 20 rows
- Responsive: tablet hides columns, mobile switches to card list"
```

---

## Chunk 2: Polish and Verification

### Task 3: Final polish and cleanup

**Files:**
- Modify: `website/src/app/monsters/monsters.module.css` (tweaks if needed)
- Modify: `website/src/app/monsters/page.tsx` (tweaks if needed)
- Delete: `website/public/mockup-monsters-list.html` (no longer needed)

- [ ] **Step 1: Clean up the mockup file**

```bash
cd C:/Users/Administrator/Desktop/DnDMainProject/darkanddarker-wiki
rm website/public/mockup-monsters-list.html
```

- [ ] **Step 2: Full visual QA in browser**

Open `http://localhost:3000/monsters`. Check:
1. All 152 monsters render
2. Filters work: search "skeleton", filter by Boss, filter by Goblin Cave
3. Sort: click HP header — bosses with high HP should appear at top (desc)
4. Sort: click Name — alphabetical
5. Row click navigates correctly
6. Mobile layout at 375px width
7. No console errors

- [ ] **Step 3: Fix any visual issues found during QA**

Address any spacing, color, or layout issues discovered. Common things to check:
- Long monster names don't overflow
- Long dungeon lists wrap gracefully
- Monsters with no stats show "—" cleanly
- Badge text doesn't clip

- [ ] **Step 4: Commit cleanup**

```bash
cd C:/Users/Administrator/Desktop/DnDMainProject/darkanddarker-wiki
git add -A website/src/app/monsters/ website/public/mockup-monsters-list.html
git commit -m "chore(monsters): remove design mockup, polish table styles"
```

---

**End of plan.**
