"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import styles from "./items.module.css";

// ---------------------------------------------------------------------------
// Types matching the JSON output from build_item_search.py
// ---------------------------------------------------------------------------

interface ItemsData {
  generated_at: string;
  dungeons: { n: string; g: [number, string][] }[];
  rarities: string[];
  luck_curve: number[][];
  modules: string[];
  module_display: string[];
  items: string[];
  item_meta: Record<string, { dn: string; it: string; st: string; at: string }>;
  item_icons: Record<string, string>;
  item_pools: Record<string, [number, number, number][]>;
  pools: { n: string; g: Record<string, number[]> }[];
  rates: number[][];
  sources: [number, number, string, string, number, [number, string, [number, number, number][], number][], number[]][];
  fixed_rarity: Record<string, number>;
}

interface ComputedResult {
  dungeon: string;
  dungeonIdx: number;
  grade: number;
  gradeLabel: string;
  sourceName: string;
  category: string;
  variantName: string;
  variantPct: number;
  prob: number;
  rarity: number;
  poolName: string;
  poolSize: number;
  lgPct: number;
  rolls: number;
  interactCount: number;
  perSearchProb: number;
  modules: string[];
  moduleDisplayNames: string[];
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const RARITY_COLORS: Record<string, string> = {
  Poor: "#888", Common: "#ccc", Uncommon: "#2bab2b", Rare: "#4488dd",
  Epic: "#9b2bab", Legendary: "#c9a84c", Unique: "#e05050", Artifact: "#e08020",
};

const DIFF_COLORS: Record<string, { bg: string; color: string }> = {
  Adventure:    { bg: "rgba(43,171,43,0.12)", color: "#4cdb4c" },
  Normal:       { bg: "rgba(201,168,76,0.12)", color: "#c9a84c" },
  "High Roller": { bg: "rgba(171,43,43,0.12)", color: "#e05050" },
};

const CAT_COLORS: Record<string, string> = {
  Monster: "#e05555", TreasureHoard: "#c9a84c", MarvelousChest: "#c9a84c",
  GoldChest: "#c9a84c", OrnateChest: "#9b8b5a", SpecialChest: "#8888cc",
  WoodChest: "#8b7044", SimpleChest: "#8b7044", Chest: "#7a6540",
  Coffin: "#7a7a7a", Equipment: "#5588dd", Consumable: "#55c075",
  Valuable: "#c9a84c", Herb: "#55c075", Ore: "#aa8855",
  SeaCreature: "#5588aa", QuestItem: "#9b2bab", Container: "#8b7044",
};

const PAGE_SIZE = 50;

function formatModule(m: string, displayName?: string): string {
  if (displayName) return displayName;
  return m.replace(/_/g, " ").replace(/([a-z])([A-Z])/g, "$1 $2").replace(/([A-Z]+)([A-Z][a-z])/g, "$1 $2").replace(/(\D)(\d)/g, "$1 $2").replace(/(\d)([A-Za-z])/g, "$1 $2").trim();
}

// ---------------------------------------------------------------------------
// Probability computation (unchanged)
// ---------------------------------------------------------------------------

function getLuckMult(luckCurve: number[][], lg: number, luck: number): number {
  if (luck <= 0 || lg < 0 || lg > 8) return 1;
  const idx = Math.min(luck * 2, 10);
  const lo = Math.floor(idx);
  const hi = Math.min(lo + 1, 10);
  const frac = idx - lo;
  return luckCurve[lg][lo] + frac * (luckCurve[lg][hi] - luckCurve[lg][lo]);
}

function getModRates(data: ItemsData, ri: number, luck: number): { modRates: number[]; modTotal: number } {
  const rates = data.rates[ri];
  let modTotal = 0;
  const modRates = new Array(9);
  for (let g = 0; g < 9; g++) {
    modRates[g] = (rates[g] || 0) * getLuckMult(data.luck_curve, g, luck);
    modTotal += modRates[g];
  }
  return { modRates, modTotal };
}

function computeVariantProb(
  data: ItemsData, itemIdx: number, poolRefs: [number, number, number][],
  filterRarity: number, luck: number,
): { prob: number; poolName: string; rarity: number; poolSize: number; lgPct: number; rolls: number } | null {
  const itemPools = data.item_pools[String(itemIdx)] || [];
  const isFixed = data.fixed_rarity[String(itemIdx)] !== undefined;
  const fixedRar = isFixed ? data.fixed_rarity[String(itemIdx)] : 0;
  if (isFixed && filterRarity > 0 && fixedRar !== filterRarity) return null;
  let probNotGetting = 1;
  let hasItem = false;
  let poolName = "", itemRarity = 0, poolSize = 0, lgPct = 0, relevantRolls = 0;
  for (const [pi, ri, count] of poolRefs) {
    const { modRates, modTotal } = getModRates(data, ri, luck);
    if (modTotal === 0) continue;
    let poolRelevant = false;
    for (const [poolIdx, lg, countAtLG] of itemPools) {
      if (poolIdx !== pi) continue;
      if (!isFixed && filterRarity > 0 && lg !== filterRarity) continue;
      const rateForLG = modRates[lg] || 0;
      if (rateForLG === 0) continue;
      const pOneRoll = (rateForLG / modTotal) * (1 / countAtLG);
      const pFromPool = 1 - Math.pow(1 - pOneRoll, count);
      probNotGetting *= (1 - pFromPool);
      hasItem = true;
      poolRelevant = true;
      if (!poolName) {
        poolName = data.pools[pi].n;
        itemRarity = isFixed ? fixedRar : lg;
        poolSize = countAtLG;
        lgPct = (rateForLG / modTotal) * 100;
      }
    }
    if (poolRelevant) relevantRolls += count;
  }
  if (!hasItem) return null;
  return { prob: 1 - probNotGetting, poolName, rarity: itemRarity, poolSize, lgPct, rolls: relevantRolls };
}

function computeSourceRarityProb(
  data: ItemsData, poolRefs: [number, number, number][], targetLG: number, luck: number,
): { prob: number; rolls: number } | null {
  let probNot = 1, rolls = 0, hasRate = false;
  for (const [pi, ri, count] of poolRefs) {
    const { modRates, modTotal } = getModRates(data, ri, luck);
    if (modTotal === 0) continue;
    const rateForLG = modRates[targetLG] || 0;
    if (rateForLG === 0) continue;
    const pOneRoll = rateForLG / modTotal;
    const pFromPool = 1 - Math.pow(1 - pOneRoll, count);
    probNot *= (1 - pFromPool);
    rolls += count;
    hasRate = true;
  }
  if (!hasRate) return null;
  return { prob: 1 - probNot, rolls };
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ModuleList({ modules, displayNames }: { modules: string[]; displayNames?: string[] }) {
  const [expanded, setExpanded] = useState(false);
  const formatted = modules.map((m, i) => formatModule(m, displayNames?.[i]));
  if (modules.length === 0) return <span style={{ color: "var(--text-muted)" }}>&mdash;</span>;
  if (modules.length <= 2) return <>{formatted.join(", ")}</>;
  return (
    <span>
      {expanded ? formatted.join(", ") : formatted.slice(0, 2).join(", ")}
      <button className={styles.moduleExpandBtn} onClick={() => setExpanded(!expanded)}>
        {expanded ? "show less" : `+${modules.length - 2} more`}
      </button>
    </span>
  );
}

function ItemIcon({ data, itemIdx, size = 32 }: { data: ItemsData; itemIdx: number; size?: number }) {
  const icon = data.item_icons[String(itemIdx)];
  if (!icon) return null;
  return (
    <img src={`/item-icons/${icon}.png`} alt="" width={size} height={size}
      style={{ imageRendering: "pixelated", verticalAlign: "middle", flexShrink: 0 }} loading="lazy" />
  );
}

function RarityBadge({ rarity, small }: { rarity: string; small?: boolean }) {
  const color = RARITY_COLORS[rarity] ?? "#aaa";
  return (
    <span className={small ? styles.badgeSmall : styles.badge}
      style={{ color, background: `${color}18`, border: `1px solid ${color}33` }}>
      {rarity}
    </span>
  );
}

function DiffBadge({ diff }: { diff: string }) {
  const s = DIFF_COLORS[diff] ?? { bg: "rgba(255,255,255,0.06)", color: "#aaa" };
  return (
    <span className={styles.badge} style={{ color: s.color, background: s.bg, border: `1px solid ${s.color}44` }}>
      {diff}
    </span>
  );
}

function CatBadge({ cat }: { cat: string }) {
  const color = CAT_COLORS[cat] ?? "#aaa";
  const label = cat.replace(/([a-z])([A-Z])/g, "$1 $2");
  return (
    <span className={styles.badge} style={{ color, background: `${color}18`, border: `1px solid ${color}33` }}>
      {label}
    </span>
  );
}

function ProbBar({ prob }: { prob: number }) {
  const pct = prob * 100;
  const barWidth = Math.max(0.5, pct);
  const color = pct >= 10 ? "#55c075" : pct >= 2 ? "#c9a84c" : "#e05555";
  const textClass = pct >= 10 ? styles.probTextHigh : pct >= 2 ? styles.probTextMid : styles.probTextLow;
  const text = pct >= 0.01 ? `${pct.toFixed(2)}%` : pct >= 0.001 ? `${pct.toFixed(3)}%` : "< 0.001%";
  return (
    <div className={styles.probWrap}>
      <span className={textClass}>{text}</span>
      <div className={styles.probBarOuter}>
        <div className={styles.probBarInner}
          style={{ width: `${barWidth}%`, background: `linear-gradient(90deg, ${color}88, ${color}30)` }} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function ItemSearch() {
  const [data, setData] = useState<ItemsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [selectedItem, setSelectedItem] = useState<number>(-1);
  const [filterRarity, setFilterRarity] = useState(0);
  const [filterDungeon, setFilterDungeon] = useState(-1);
  const [filterDiff, setFilterDiff] = useState("all");
  const [playerLuck, setPlayerLuck] = useState(0);
  const [sortCol, setSortCol] = useState<string>("prob");
  const [sortAsc, setSortAsc] = useState(false);
  const [page, setPage] = useState(1);
  const [showSuggestions, setShowSuggestions] = useState(false);

  // Read ?search= param from URL on mount
  const [urlSearch, setUrlSearch] = useState<string | null>(null);
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const q = params.get("search");
    if (q) {
      setSearch(q);
      setUrlSearch(q);
    }
  }, []);

  useEffect(() => {
    fetch("/data/items.json")
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then((d: ItemsData) => { setData(d); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, []);

  const searchIndex = useMemo(() => {
    if (!data) return [];
    return data.items.map((name, i) => {
      const meta = data.item_meta[String(i)];
      const dn = meta?.dn ?? name;
      return { name: name.toLowerCase(), dn: dn.toLowerCase(), idx: i, display: dn, assetName: name };
    });
  }, [data]);

  // Auto-select first match when arriving via URL ?search= param
  useEffect(() => {
    if (!urlSearch || !data || searchIndex.length === 0) return;
    const q = urlSearch.trim().toLowerCase();
    const match = searchIndex.find(
      (item) => item.dn === q || item.name === q
    ) ?? searchIndex.find(
      (item) => item.dn.startsWith(q) || item.name.startsWith(q)
    );
    if (match) {
      setSelectedItem(match.idx);
      setUrlSearch(null);
    }
  }, [urlSearch, data, searchIndex]);

  const suggestions = useMemo(() => {
    if (!data || search.trim().length < 2) return [];
    const q = search.trim().toLowerCase();
    const matches: { name: string; dn: string; idx: number; display: string; assetName: string; score: number }[] = [];
    for (const item of searchIndex) {
      if (item.name.startsWith(q) || item.dn.startsWith(q)) matches.push({ ...item, score: 2 });
      else if (item.name.includes(q) || item.dn.includes(q)) matches.push({ ...item, score: 1 });
    }
    matches.sort((a, b) => b.score - a.score || a.name.localeCompare(b.name));
    return matches.slice(0, 30);
  }, [data, search, searchIndex]);

  const getItemRarities = useCallback((idx: number): number[] => {
    if (!data) return [];
    const isFixed = data.fixed_rarity[String(idx)] !== undefined;
    if (isFixed) return [data.fixed_rarity[String(idx)]];
    const pools = data.item_pools[String(idx)] || [];
    return [...new Set(pools.map(p => p[1]))].sort((a, b) => a - b);
  }, [data]);

  const isBrowseMode = selectedItem < 0 && filterRarity > 0;

  // Item search results
  const itemResults = useMemo(() => {
    if (!data || selectedItem < 0) return [];
    const itemPools = data.item_pools[String(selectedItem)] || [];
    if (!itemPools.length) return [];
    const isFixed = data.fixed_rarity[String(selectedItem)] !== undefined;
    const fixedRar = isFixed ? data.fixed_rarity[String(selectedItem)] : 0;
    if (filterRarity > 0) {
      if (isFixed && fixedRar !== filterRarity) return [];
      if (!isFixed) {
        const rarities = [...new Set(itemPools.map(p => p[1]))];
        if (!rarities.includes(filterRarity)) return [];
      }
    }
    const relevantPoolIdxs = new Set<number>();
    for (const [pi, lg] of itemPools) {
      if (!isFixed && filterRarity > 0 && lg !== filterRarity) continue;
      relevantPoolIdxs.add(pi);
    }
    const computed: ComputedResult[] = [];
    for (const src of data.sources) {
      const [dIdx, grade, name, cat, totalRate, vgroups, moduleIdxs = []] = src;
      if (filterDungeon >= 0 && dIdx !== filterDungeon) continue;
      const gMod = grade % 10000;
      const diffKey = gMod >= 1000 && gMod < 2000 ? "adv" : gMod >= 2000 && gMod < 3000 ? "norm" : "hr";
      if (filterDiff !== "all" && diffKey !== filterDiff) continue;
      const dungeon = data.dungeons[dIdx];
      const gradeEntry = dungeon.g.find(g => g[0] === grade);
      const gradeLabel = gradeEntry ? gradeEntry[1] : "";
      const modules = moduleIdxs.map(mi => data.modules[mi] || "?");
      const moduleDisplayNames = moduleIdxs.map(mi => data.module_display?.[mi] || "");
      for (const vg of vgroups) {
        const [spawnRate, vname, poolRefs, interactCount = 0] = vg;
        let hasPool = false;
        for (const [pi] of poolRefs) { if (relevantPoolIdxs.has(pi)) { hasPool = true; break; } }
        if (!hasPool) continue;
        const res = computeVariantProb(data, selectedItem, poolRefs, filterRarity, playerLuck);
        if (!res || res.prob <= 0) continue;
        const variantPct = totalRate > 0 ? spawnRate / totalRate : 1;
        const displayName = vname && vgroups.length > 1 ? `${name} (${vname})` : (vname || name);
        const perSearchProb = res.prob;
        const finalProb = interactCount > 1 ? 1 - Math.pow(1 - perSearchProb, interactCount) : perSearchProb;
        computed.push({
          ...res, prob: finalProb, perSearchProb, interactCount, modules, moduleDisplayNames,
          dungeon: dungeon.n, dungeonIdx: dIdx, grade, gradeLabel, sourceName: displayName,
          category: cat, variantName: vname, variantPct,
        });
      }
    }
    const dir = sortAsc ? 1 : -1;
    computed.sort((a, b) => {
      switch (sortCol) {
        case "prob": return dir * (a.prob - b.prob);
        case "dungeon": return dir * a.dungeon.localeCompare(b.dungeon);
        case "grade": return dir * (a.grade - b.grade);
        case "source": return dir * a.sourceName.localeCompare(b.sourceName);
        case "type": return dir * a.category.localeCompare(b.category);
        case "module": return dir * (a.modules[0] || "").localeCompare(b.modules[0] || "");
        default: return dir * (a.prob - b.prob);
      }
    });
    return computed;
  }, [data, selectedItem, filterRarity, filterDungeon, filterDiff, playerLuck, sortCol, sortAsc]);

  // Browse mode results
  const browseResults = useMemo(() => {
    if (!data || !isBrowseMode) return [];
    const computed: ComputedResult[] = [];
    for (const src of data.sources) {
      const [dIdx, grade, name, cat, totalRate, vgroups, moduleIdxs = []] = src;
      if (filterDungeon >= 0 && dIdx !== filterDungeon) continue;
      const gMod = grade % 10000;
      const diffKey = gMod >= 1000 && gMod < 2000 ? "adv" : gMod >= 2000 && gMod < 3000 ? "norm" : "hr";
      if (filterDiff !== "all" && diffKey !== filterDiff) continue;
      const dungeon = data.dungeons[dIdx];
      const gradeEntry = dungeon.g.find(g => g[0] === grade);
      const gradeLabel = gradeEntry ? gradeEntry[1] : "";
      const modules = moduleIdxs.map(mi => data.modules[mi] || "?");
      const moduleDisplayNames = moduleIdxs.map(mi => data.module_display?.[mi] || "");
      for (const vg of vgroups) {
        const [spawnRate, vname, poolRefs, interactCount = 0] = vg;
        const res = computeSourceRarityProb(data, poolRefs, filterRarity, playerLuck);
        if (!res || res.prob <= 0) continue;
        const variantPct = totalRate > 0 ? spawnRate / totalRate : 1;
        const displayName = vname && vgroups.length > 1 ? `${name} (${vname})` : (vname || name);
        const perSearchProb = res.prob;
        const finalProb = interactCount > 1 ? 1 - Math.pow(1 - perSearchProb, interactCount) : perSearchProb;
        computed.push({
          prob: finalProb, perSearchProb, interactCount, modules, moduleDisplayNames,
          poolName: "", rarity: filterRarity, poolSize: 0, lgPct: 0, rolls: res.rolls,
          dungeon: dungeon.n, dungeonIdx: dIdx, grade, gradeLabel, sourceName: displayName,
          category: cat, variantName: vname, variantPct,
        });
      }
    }
    const dir = sortAsc ? 1 : -1;
    computed.sort((a, b) => {
      switch (sortCol) {
        case "prob": return dir * (a.prob - b.prob);
        case "dungeon": return dir * a.dungeon.localeCompare(b.dungeon);
        case "grade": return dir * (a.grade - b.grade);
        case "source": return dir * a.sourceName.localeCompare(b.sourceName);
        case "type": return dir * a.category.localeCompare(b.category);
        case "module": return dir * (a.modules[0] || "").localeCompare(b.modules[0] || "");
        default: return dir * (a.prob - b.prob);
      }
    });
    return computed;
  }, [data, isBrowseMode, filterRarity, filterDungeon, filterDiff, playerLuck, sortCol, sortAsc]);

  const results = isBrowseMode ? browseResults : itemResults;

  const selectItem = useCallback((idx: number, displayName: string) => {
    setSelectedItem(idx);
    setSearch(displayName);
    setShowSuggestions(false);
    setPage(1);
  }, []);

  const handleSort = useCallback((col: string) => {
    if (sortCol === col) setSortAsc(!sortAsc);
    else { setSortCol(col); setSortAsc(col === "prob" ? false : true); }
  }, [sortCol, sortAsc]);

  const totalPages = Math.ceil(results.length / PAGE_SIZE);
  const visibleResults = results.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  // -- Loading --
  if (loading) {
    return (
      <div className={styles.loadingWrap}>
        <div className={styles.spinner} />
        <p className={styles.loadingText}>Loading Item Database...</p>
      </div>
    );
  }

  // -- Error --
  if (error) {
    return <div className={styles.emptyState} style={{ color: "var(--red-300)", minHeight: "100vh", paddingTop: "var(--nav-h)" }}>Failed to load: {error}</div>;
  }

  const itemName = selectedItem >= 0 ? (data?.item_meta[String(selectedItem)]?.dn || data?.items[selectedItem] || "") : "";
  const isFixed = selectedItem >= 0 && data?.fixed_rarity[String(selectedItem)] !== undefined;
  const showResults = results.length > 0;
  const showEmpty = (selectedItem >= 0 || isBrowseMode) && results.length === 0;
  const showPrompt = selectedItem < 0 && !isBrowseMode;

  const COLS = [
    { key: "prob", label: "Drop Chance", sortable: true },
    { key: "dungeon", label: "Dungeon", sortable: true },
    { key: "grade", label: "Difficulty", sortable: true },
    { key: "source", label: "Source", sortable: true },
    { key: "type", label: "Type", sortable: true },
    { key: "module", label: "Module", sortable: true },
    ...(isBrowseMode ? [] : [{ key: "pool", label: "Pool Context", sortable: false }]),
  ];

  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.header}>
        <span className={styles.headerLabel}>Arsenal</span>
        <h1 className={styles.headerTitle}>Item Finder</h1>
        <p className={styles.headerDesc}>
          Search for an item to see where it drops, or select a rarity to browse all sources.
        </p>

        {/* Search */}
        <div className={styles.searchWrap}>
          <span className={styles.searchIcon}>&#x1F50D;</span>
          <input
            type="text"
            placeholder="Search items..."
            value={search}
            onChange={e => {
              setSearch(e.target.value);
              setShowSuggestions(true);
              if (!e.target.value.trim()) { setSelectedItem(-1); setPage(1); }
            }}
            onFocus={() => search.trim().length >= 2 && setShowSuggestions(true)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
            className={styles.searchInput}
          />
          {showSuggestions && suggestions.length > 0 && (
            <div className={styles.suggestions}>
              {suggestions.map(s => {
                const rarities = getItemRarities(s.idx);
                return (
                  <div key={s.idx} className={styles.suggestionItem}
                    onMouseDown={e => { e.preventDefault(); selectItem(s.idx, s.display); }}>
                    <span className={styles.suggestionLeft}>
                      {data && <ItemIcon data={data} itemIdx={s.idx} size={28} />}
                      {s.display}
                    </span>
                    <span className={styles.suggestionRarities}>
                      {rarities.map(r => <RarityBadge key={r} rarity={data?.rarities[r] ?? "?"} small />)}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Filter Bar */}
      <div className={styles.filterBar}>
        <div className={styles.filterInner}>
          <div className={styles.filterGroup}>
            <span className={styles.filterLabel}>Rarity</span>
            <select value={filterRarity} onChange={e => { setFilterRarity(Number(e.target.value)); setPage(1); }} className={styles.filterSelect}>
              <option value={0}>All Rarities</option>
              {(data?.rarities ?? []).slice(1).map((r, i) => <option key={r} value={i + 1}>{r}</option>)}
            </select>
          </div>
          <div className={styles.filterGroup}>
            <span className={styles.filterLabel}>Difficulty</span>
            <select value={filterDiff} onChange={e => { setFilterDiff(e.target.value); setPage(1); }} className={styles.filterSelect}>
              <option value="all">All Difficulties</option>
              <option value="adv">Adventure</option>
              <option value="norm">Normal</option>
              <option value="hr">High Roller</option>
            </select>
          </div>
          <div className={styles.filterGroup}>
            <span className={styles.filterLabel}>Dungeon</span>
            <select value={filterDungeon} onChange={e => { setFilterDungeon(Number(e.target.value)); setPage(1); }} className={styles.filterSelect}>
              <option value={-1}>All Dungeons</option>
              {(data?.dungeons ?? []).map((d, i) => <option key={d.n} value={i}>{d.n}</option>)}
            </select>
          </div>
          <div className={styles.filterGroup}>
            <span className={styles.filterLabel}>Luck</span>
            <input type="range" min={0} max={50} step={5} value={playerLuck * 10}
              onChange={e => { setPlayerLuck(parseInt(e.target.value) / 10); setPage(1); }}
              style={{ width: 70, accentColor: "var(--gold-500)" }} />
            <span className={styles.luckValue}>{playerLuck.toFixed(1)}</span>
          </div>
        </div>
      </div>

      {/* Results */}
      <div className={styles.resultsArea}>
        {showPrompt && (
          <div className={styles.emptyState}>
            Type an item name above to find where it drops, or select a rarity to browse all sources
          </div>
        )}

        {showEmpty && (
          <div className={styles.emptyState}>
            No sources found{itemName ? ` for ${itemName}` : ""} with current filters
          </div>
        )}

        {showResults && (
          <>
            {/* Results Header */}
            <div className={styles.resultsHeader}>
              <div className={styles.resultsItemInfo}>
                {selectedItem >= 0 && data && <ItemIcon data={data} itemIdx={selectedItem} size={40} />}
                <div>
                  <span className={styles.resultsItemName}>
                    {isBrowseMode ? `All ${data?.rarities[filterRarity]} Items` : itemName}
                  </span>
                  {isFixed && data && (
                    <span style={{ marginLeft: 8 }}>
                      <RarityBadge rarity={data.rarities[data.fixed_rarity[String(selectedItem)]] ?? "?"} />
                      <span style={{ fontSize: 10, color: "var(--text-muted)", marginLeft: 4 }}>(fixed)</span>
                    </span>
                  )}
                  {!isFixed && !isBrowseMode && filterRarity > 0 && data && (
                    <span style={{ marginLeft: 8 }}><RarityBadge rarity={data.rarities[filterRarity] ?? "?"} /></span>
                  )}
                  {playerLuck > 0 && (
                    <span style={{ fontSize: 11, color: "var(--gold-500)", marginLeft: 8 }}>[Luck {playerLuck.toFixed(1)}]</span>
                  )}
                </div>
              </div>
              <span className={styles.resultsCount}>
                {results.length} source{results.length !== 1 ? "s" : ""}
                {totalPages > 1 && ` \u2014 Page ${page}/${totalPages}`}
              </span>
            </div>

            {/* Table */}
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    {COLS.map(col => (
                      <th key={col.key}
                        onClick={() => col.sortable && handleSort(col.key)}
                        className={`${styles.th} ${sortCol === col.key ? styles.thActive : ""} ${!col.sortable ? styles.thNoSort : ""}`}>
                        {col.label}
                        {sortCol === col.key && <span style={{ marginLeft: 4 }}>{sortAsc ? "\u25B2" : "\u25BC"}</span>}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {visibleResults.map((r, i) => (
                    <tr key={i} className={styles.tr}>
                      <td className={styles.td}>
                        <ProbBar prob={r.prob} />
                        {(r.interactCount > 1 || r.rolls > 1) && (
                          <div className={styles.probMeta}>
                            {r.rolls > 1 && <span>{r.rolls} rolls{r.interactCount > 1 ? "/search" : ""}</span>}
                            {r.interactCount > 1 && (
                              <>
                                {r.rolls > 1 && <span style={{ margin: "0 4px" }}>&middot;</span>}
                                <span className={styles.probSearches}>{r.interactCount} searches</span>
                                <span style={{ margin: "0 4px" }}>&middot;</span>
                                <span>per search: {(r.perSearchProb * 100).toFixed(2)}%</span>
                              </>
                            )}
                          </div>
                        )}
                      </td>
                      <td className={styles.tdDungeon}>{r.dungeon}</td>
                      <td className={styles.td}><DiffBadge diff={r.gradeLabel} /></td>
                      <td className={styles.tdSource}>
                        {r.sourceName}
                        {r.variantPct < 1 && <div className={styles.variantLabel}>{(r.variantPct * 100).toFixed(1)}% variant</div>}
                      </td>
                      <td className={styles.td}><CatBadge cat={r.category} /></td>
                      <td className={styles.tdModules}>
                        <ModuleList modules={r.modules} displayNames={r.moduleDisplayNames} />
                      </td>
                      {!isBrowseMode && (
                        <td className={styles.tdPool}>
                          <span className={styles.poolName}>{r.poolName}</span>
                          <span className={styles.poolSize}>{r.poolSize} items in pool</span>
                          {r.lgPct > 0 && (
                            <div className={styles.poolDetail}>
                              rarity roll: {r.lgPct.toFixed(1)}% &rarr; 1/{r.poolSize} = {(r.lgPct / r.poolSize).toFixed(2)}%/roll
                            </div>
                          )}
                          {r.rarity > 0 && data && (
                            <div style={{ marginTop: 2 }}><RarityBadge rarity={data.rarities[r.rarity] ?? "?"} small /></div>
                          )}
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className={styles.pagination}>
                <button disabled={page === 1} onClick={() => setPage(p => Math.max(1, p - 1))} className={styles.pageBtnNav}>
                  &larr; Prev
                </button>
                {Array.from({ length: Math.min(7, totalPages) }, (_, i) => {
                  let p: number;
                  if (totalPages <= 7) p = i + 1;
                  else if (page <= 4) p = i + 1;
                  else if (page >= totalPages - 3) p = totalPages - 6 + i;
                  else p = page - 3 + i;
                  return (
                    <button key={p} onClick={() => setPage(p)}
                      className={p === page ? styles.pageBtnActive : styles.pageBtn}>
                      {p}
                    </button>
                  );
                })}
                <button disabled={page === totalPages} onClick={() => setPage(p => Math.min(totalPages, p + 1))} className={styles.pageBtnNav}>
                  Next &rarr;
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
