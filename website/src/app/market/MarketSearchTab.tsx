"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import styles from "./market.module.css";
import { searchItems, fetchRawListings, fetchPriceHistory, GOLD_ICON, itemIconPath, type ItemDef, type RawListing, type PricePoint } from "./api";
import ItemTooltip from "./ItemTooltip";
import { cleanStatName, formatStatValue, isPercentStat } from "./statFormat";
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";

const BASE_RARITIES = ["Poor", "Common", "Uncommon", "Rare", "Epic", "Legendary", "Unique", "Artifact"];
const RARITY_SECONDARY_SLOTS: Record<string, number> = {
  Common: 1, Uncommon: 1, Rare: 2, Epic: 3, Legendary: 4, Unique: 1,
};

interface ItemMeta {
  name: string;
  fixedRarity: string | null;
  secondarySlots: number;
  itemType: string;
  [key: string]: unknown;
}

function timeAgo(epoch: number): string {
  const sec = Math.floor(Date.now() / 1000 - epoch);
  if (sec < 60) return `${sec}s ago`;
  if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
  if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`;
  return `${Math.floor(sec / 86400)}d ago`;
}

function formatGold(n: number): string {
  if (!n || isNaN(n)) return "—";
  return Math.round(n).toLocaleString();
}

function formatChartTime(ts: string, timeframe: string): string {
  const d = new Date(ts);
  if (timeframe === "1d") return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  if (timeframe === "4h") return d.toLocaleDateString("en-US", { weekday: "short" }) + " " + d.getHours().toString().padStart(2, "0") + ":00";
  return d.getHours().toString().padStart(2, "0") + ":" + d.getMinutes().toString().padStart(2, "0");
}

// Get proper display name for an item
function getItemDisplayName(baseName: string, metadata: Record<string, ItemMeta>): string {
  const meta = metadata[baseName];
  if (meta?.name) return meta.name;
  return baseName.replace(/([A-Z])/g, " $1").trim();
}

interface PropertyFilter { name: string; label: string; min: string; }

export default function MarketSearchTab() {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<ItemDef[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedItem, setSelectedItem] = useState<{ id: string; name: string; archetype: string } | null>(null);
  const [selectedRarity, setSelectedRarity] = useState("");
  const [propFilters, setPropFilters] = useState<PropertyFilter[]>([]);
  const [activeListings, setActiveListings] = useState<RawListing[]>([]);
  const [soldListings, setSoldListings] = useState<RawListing[]>([]);
  const [priceHistory, setPriceHistory] = useState<PricePoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [previewListing, setPreviewListing] = useState<RawListing | null>(null);
  const [chartTimeframe, setChartTimeframe] = useState<"1d" | "4h" | "1h">("4h");
  const [isGenericItem, setIsGenericItem] = useState(false);
  const [availableProps, setAvailableProps] = useState<string[]>([]);
  const [itemMetadata, setItemMetadata] = useState<Record<string, ItemMeta>>({});

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch("/data/item_metadata.json").then((r) => r.json()).then((d) => setItemMetadata(d)).catch(() => {});
  }, []);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) setShowSuggestions(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleSelectItem = useCallback((item: ItemDef) => {
    setSelectedItem({ id: item.id, name: item.name, archetype: item.archetype });
    setQuery(item.name);
    setShowSuggestions(false);
    setSuggestions([]);
    const meta = itemMetadata[item.archetype];
    if (meta?.fixedRarity) setSelectedRarity("");
  }, [itemMetadata]);

  const handleQueryChange = useCallback((val: string) => {
    setQuery(val);
    setSelectedItem(null);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (val.trim().length < 2) { setSuggestions([]); setShowSuggestions(false); return; }
    debounceRef.current = setTimeout(() => {
      const ac = new AbortController();
      searchItems(val.trim(), 20, ac.signal)
        .then((items) => {
          const seen = new Set<string>();
          setSuggestions(items.filter((i) => { if (seen.has(i.archetype)) return false; seen.add(i.archetype); return true; }));
          setShowSuggestions(true);
        }).catch(() => {});
    }, 250);
  }, []);

  const getStatSlotCount = (): number => {
    // Rarity determines slot count (Rare=2, Epic=3, Legendary=4, etc.)
    if (selectedRarity) return RARITY_SECONDARY_SLOTS[selectedRarity] || 0;
    // No rarity selected — use item metadata as fallback
    if (selectedItem) {
      const meta = itemMetadata[selectedItem.archetype];
      if (meta?.secondarySlots) return meta.secondarySlots;
    }
    return 0;
  };

  const canSearch = selectedItem || selectedRarity;

  const doSearch = useCallback(async () => {
    if (!canSearch) return;
    if (abortRef.current) abortRef.current.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setLoading(true); setSearched(true); setPreviewListing(null);

    const itemArch = selectedItem?.archetype || "";
    try {
      const [active, sold, history] = await Promise.all([
        fetchRawListings(itemArch, { base_rarity: selectedRarity || undefined, status: "active", limit: 500, sort: "price_asc" }, ac.signal),
        fetchRawListings(itemArch, { base_rarity: selectedRarity || undefined, status: "sold", limit: 100, sort: "sold_desc" }, ac.signal),
        itemArch ? fetchPriceHistory(itemArch, chartTimeframe === "1d" ? "1d" : chartTimeframe === "4h" ? "4h" : "1h", ac.signal) : Promise.resolve([]),
      ]);
      if (!ac.signal.aborted) {
        setActiveListings(active); setSoldListings(sold); setPriceHistory(history);
        setIsGenericItem(active.length > 0 && active.every((l) => l.base_rarity === "Unknown"));
        const ps = new Set<string>();
        for (const l of active) for (const p of l.properties) if (!p.is_primary) ps.add(p.property_type);
        setAvailableProps(Array.from(ps).sort());
        const slotCount = getStatSlotCount();
        if (slotCount > 0) {
          // Always reset filter slots to match current rarity's slot count
          setPropFilters(Array.from({ length: slotCount }, () => ({ name: "", label: "Any", min: "" })));
        } else {
          setPropFilters([]);
        }
        setLoading(false);
      }
    } catch { if (!ac.signal.aborted) setLoading(false); }
  }, [selectedItem, selectedRarity, chartTimeframe, canSearch]);

  useEffect(() => {
    if (!searched || !selectedItem) return;
    const ac = new AbortController();
    fetchPriceHistory(selectedItem.archetype, chartTimeframe === "1d" ? "1d" : chartTimeframe === "4h" ? "4h" : "1h", ac.signal)
      .then((h) => { if (!ac.signal.aborted) setPriceHistory(h); }).catch(() => {});
    return () => ac.abort();
  }, [chartTimeframe, searched, selectedItem]);

  // Convert user input to raw DB value for filtering
  const userInputToRawValue = (propName: string, userVal: string): number => {
    const num = parseFloat(userVal);
    if (isNaN(num)) return 0;
    if (isPercentStat(propName)) return Math.round(num * 10); // 2.3% → 23 raw
    return num;
  };

  const applyPropFilters = (listing: RawListing) => {
    for (const f of propFilters) {
      if (!f.name) continue;
      const prop = listing.properties.find((p) => p.property_type === f.name && !p.is_primary);
      if (!prop) return false;
      if (f.min) {
        const rawMin = userInputToRawValue(f.name, f.min);
        if (prop.property_value < rawMin) return false;
      }
    }
    return true;
  };
  const filteredActive = activeListings.filter(applyPropFilters);
  const filteredSold = soldListings.filter(applyPropFilters).slice(0, 10);
  const handleKeyDown = (e: React.KeyboardEvent) => { if (e.key === "Enter" && canSearch) doSearch(); };

  const now_s = Date.now() / 1000;
  const avgPrice = (since: number) => {
    const p = soldListings.filter((l) => l.sold_at && l.sold_at > since).map((l) => l.price / Math.max(l.item_count, 1));
    return p.length ? Math.round(p.reduce((a, b) => a + b, 0) / p.length) : 0;
  };
  const lowestNow = activeListings.length > 0 ? activeListings[0].price / Math.max(activeListings[0].item_count, 1) : 0;

  const showHero = searched && selectedItem;
  const isRarityOnly = searched && !selectedItem && selectedRarity !== "";
  const showStatFilters = searched && availableProps.length > 0 && !isGenericItem;
  const statSlotCount = getStatSlotCount();

  return (
    <div className={styles.dashboard}>
      {/* ── Search Bar ── */}
      <div className={styles.msSearchBar} ref={wrapperRef}>
        <div className={styles.msSearchInputWrap}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ opacity: 0.4, flexShrink: 0 }}>
            <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input type="text" className={styles.msSearchInput} placeholder="Search item name or select rarity..."
            value={query} onChange={(e) => handleQueryChange(e.target.value)}
            onFocus={() => { if (suggestions.length > 0) setShowSuggestions(true); }}
            onKeyDown={handleKeyDown} />
        </div>
        <select className={styles.msSelect} value={selectedRarity} onChange={(e) => setSelectedRarity(e.target.value)}>
          <option value="">All Rarities</option>
          {BASE_RARITIES.map((r) => (<option key={r} value={r}>{r}</option>))}
        </select>
        <button className={styles.msSearchBtn} onClick={doSearch} disabled={!canSearch || loading}>
          {loading ? "..." : "Search"}
        </button>
        {showSuggestions && suggestions.length > 0 && (
          <div className={styles.msSuggestions}>
            {suggestions.map((item) => {
              const meta = itemMetadata[item.archetype];
              return (
                <div key={item.id} className={styles.msSuggestionItem} onClick={() => handleSelectItem(item)}>
                  <img src={itemIconPath(item.archetype)} width={20} height={20} alt=""
                    onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
                  <span>{item.name}</span>
                  {meta?.fixedRarity && (
                    <span className={styles[`rarity${meta.fixedRarity}`]} style={{ fontSize: "0.65rem", marginLeft: "auto" }}>
                      {meta.fixedRarity}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Attributes (moved under search bar) ── */}
      {showStatFilters && statSlotCount > 0 && (
        <div className={styles.msFilterSection}>
          <div className={styles.sectionHeader}>
            <span className={styles.sectionTitle}>Attributes</span>
          </div>
          <div className={styles.msFilterSlots}>
            {propFilters.slice(0, statSlotCount).map((f, idx) => (
              <div key={idx} className={styles.msFilterSlot}>
                <select className={styles.msSelect} value={f.name}
                  onChange={(e) => {
                    const updated = [...propFilters];
                    updated[idx] = { name: e.target.value, label: e.target.value ? cleanStatName(e.target.value) : "Any", min: "" };
                    setPropFilters(updated);
                  }}>
                  <option value="">Any</option>
                  {availableProps.map((p) => (
                    <option key={p} value={p}>{cleanStatName(p)}</option>
                  ))}
                </select>
                {f.name && (
                  <input type="text" className={styles.msFilterMinInput} value={f.min}
                    placeholder={isPercentStat(f.name) ? "Min %" : "Min"}
                    onChange={(e) => {
                      const updated = [...propFilters];
                      updated[idx] = { ...f, min: e.target.value };
                      setPropFilters(updated);
                    }} />
                )}
                {f.name && isPercentStat(f.name) && <span style={{ color: "var(--text-muted)", fontSize: "0.7rem" }}>%</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Item Hero (only when specific item selected) ── */}
      {showHero && (() => {
        const meta = itemMetadata[selectedItem.archetype];
        const displayRarity = selectedRarity || meta?.fixedRarity || null;
        return (
          <div className={styles.msHero}>
            <img src={itemIconPath(selectedItem.archetype)} alt={selectedItem.name}
              width={64} height={64} className={styles.msHeroIcon}
              onError={(e) => { (e.target as HTMLImageElement).style.visibility = "hidden"; }} />
            <div>
              <h2 className={styles.msHeroName}>{selectedItem.name}</h2>
              <span style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>
                {displayRarity && <span className={styles[`rarity${displayRarity}`]} style={{ marginRight: 8 }}>{displayRarity}</span>}
                {filteredActive.length} active · {soldListings.length} sold
              </span>
            </div>
          </div>
        );
      })()}

      {/* ── Price Cards ── */}
      {searched && (
        <div className={styles.msPriceCards}>
          <div className={styles.msPriceCard}>
            <div className={styles.msPriceCardValue}>{lowestNow ? formatGold(lowestNow) : "—"}</div>
            <div className={styles.msPriceCardLabel}>Lowest Now</div>
          </div>
          <div className={styles.msPriceCard}>
            <div className={styles.msPriceCardValue}>{avgPrice(now_s - 86400) || "—"}</div>
            <div className={styles.msPriceCardLabel}>Avg 24H</div>
          </div>
          <div className={styles.msPriceCard}>
            <div className={styles.msPriceCardValue}>{avgPrice(now_s - 7 * 86400) || "—"}</div>
            <div className={styles.msPriceCardLabel}>Avg 7D</div>
          </div>
          <div className={styles.msPriceCard}>
            <div className={styles.msPriceCardValue}>{avgPrice(now_s - 14 * 86400) || "—"}</div>
            <div className={styles.msPriceCardLabel}>Avg 14D</div>
          </div>
        </div>
      )}

      {/* ── Price Chart ── */}
      {searched && selectedItem && priceHistory.length > 1 && (
        <div className={styles.msChartSection}>
          <div className={styles.msChartHeader}>
            <span className={styles.sectionTitle}>Price History</span>
            <div className={styles.msChartToggle}>
              {(["1h", "4h", "1d"] as const).map((tf) => (
                <button key={tf} className={chartTimeframe === tf ? styles.msChartBtnActive : styles.msChartBtn}
                  onClick={() => setChartTimeframe(tf)}>
                  {tf === "1h" ? "24H" : tf === "4h" ? "7D" : "14D"}
                </button>
              ))}
            </div>
          </div>
          <div className={styles.msChart}>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={priceHistory} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(201,168,76,0.08)" />
                <XAxis dataKey="timestamp" tickFormatter={(ts) => formatChartTime(ts, chartTimeframe)}
                  tick={{ fontSize: 10, fill: "#666" }} interval="preserveStartEnd" minTickGap={60} />
                <YAxis tick={{ fontSize: 10, fill: "#666" }} width={45}
                  tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(1)}k` : String(v)} />
                <Tooltip contentStyle={{ background: "rgba(20,18,14,0.95)", border: "1px solid rgba(201,168,76,0.25)", borderRadius: 6, fontSize: "0.75rem" }}
                  labelFormatter={(label) => formatChartTime(String(label), chartTimeframe)}
                  formatter={(value) => [formatGold(Number(value)) + "g", ""]} />
                <Area type="monotone" dataKey="avg" stroke="#c9a84c" fill="rgba(201,168,76,0.12)" strokeWidth={2} name="Avg" />
                <Area type="monotone" dataKey="min" stroke="rgba(76,201,100,0.4)" fill="none" strokeWidth={1} strokeDasharray="4 4" name="Min" />
                <Area type="monotone" dataKey="max" stroke="rgba(224,85,85,0.4)" fill="none" strokeWidth={1} strokeDasharray="4 4" name="Max" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* ── Item Preview ── */}
      {previewListing && selectedItem && (
        <div style={{ display: "flex", justifyContent: "center", margin: "16px 0" }}>
          <ItemTooltip itemName={selectedItem.name} rarity={previewListing.base_rarity} properties={previewListing.properties} />
        </div>
      )}

      {/* ── Active Listings ── */}
      {searched && (
        <div className={styles.msSection}>
          <div className={styles.sectionHeader}>
            <span className={styles.sectionTitle}>Active Listings ({filteredActive.length}{propFilters.some((f) => f.name) ? ` of ${activeListings.length}` : ""})</span>
          </div>
          {filteredActive.length === 0 ? (
            <div className={styles.msEmpty}>{loading ? "Loading..." : "No listings found."}</div>
          ) : (
            <div className={styles.msTableWrap}>
              <table className={styles.msTable}>
                <thead><tr>
                  {isRarityOnly && <th>Item</th>}
                  {!isGenericItem && <th style={{ width: 80 }}>Rarity</th>}
                  <th style={{ width: 90 }}>Price</th>
                  {!isGenericItem && <th>Stats</th>}
                  <th style={{ width: 70 }}>{isGenericItem ? "Qty" : "Listed"}</th>
                </tr></thead>
                <tbody>
                  {filteredActive.slice(0, 50).map((l) => (
                    <tr key={l.listing_id}
                      onClick={() => !isGenericItem && !isRarityOnly && setPreviewListing(previewListing?.listing_id === l.listing_id ? null : l)}
                      style={!isGenericItem && !isRarityOnly ? { cursor: "pointer" } : undefined}
                      className={previewListing?.listing_id === l.listing_id ? styles.msSelectedRow : ""}>
                      {isRarityOnly && (
                        <td className={styles.msItemName}>
                          <span className={styles.msItemNameInner}>
                            <img src={itemIconPath(l.item_base_name)} alt=""
                              onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
                            {getItemDisplayName(l.item_base_name, itemMetadata)}
                          </span>
                        </td>
                      )}
                      {!isGenericItem && <td><span className={styles[`rarity${l.base_rarity}`] || ""}>{l.base_rarity}</span></td>}
                      <td className={styles.msPrice}><span className={styles.msPriceInner}>{formatGold(l.price)}<img src={GOLD_ICON} alt="" width={12} height={12} /></span></td>
                      {!isGenericItem && (
                        <td className={styles.msStats}>
                          {l.properties.filter((p) => !p.is_primary).map((p, i) => (
                            <span key={i} className={styles.msStat}>{cleanStatName(p.property_type)}: {formatStatValue(p.property_type, p.property_value)}</span>
                          ))}
                          {l.properties.filter((p) => !p.is_primary).length === 0 && <span style={{ color: "var(--text-muted)" }}>—</span>}
                        </td>
                      )}
                      <td className={styles.msTime}>{isGenericItem ? l.item_count : timeAgo(l.first_seen_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {filteredActive.length > 50 && <div className={styles.msEmpty} style={{ padding: 8 }}>Showing 50 of {filteredActive.length}</div>}
            </div>
          )}
        </div>
      )}

      {/* ── Recently Sold ── */}
      {searched && soldListings.length > 0 && (
        <div className={styles.msSection}>
          <div className={styles.sectionHeader}><span className={styles.sectionTitle}>Recently Sold</span></div>
          <div className={styles.msTableWrap}>
            <table className={styles.msTable}>
              <thead><tr>
                {isRarityOnly && <th>Item</th>}
                {!isGenericItem && <th style={{ width: 80 }}>Rarity</th>}
                <th style={{ width: 90 }}>Price</th>
                {!isGenericItem && <th>Stats</th>}
                <th style={{ width: 70 }}>Sold</th>
              </tr></thead>
              <tbody>
                {filteredSold.length === 0 ? (
                  <tr><td colSpan={isRarityOnly ? 5 : isGenericItem ? 2 : 4} className={styles.msEmpty}>No sold items match filters.</td></tr>
                ) : filteredSold.map((l) => (
                  <tr key={l.listing_id} className={styles.msSoldRow}>
                    {isRarityOnly && (
                      <td className={styles.msItemName}>
                        <span className={styles.msItemNameInner}>
                          <img src={itemIconPath(l.item_base_name)} width={20} height={20} alt=""
                            onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
                          {getItemDisplayName(l.item_base_name, itemMetadata)}
                        </span>
                      </td>
                    )}
                    {!isGenericItem && <td><span className={styles[`rarity${l.base_rarity}`] || ""}>{l.base_rarity}</span></td>}
                    <td className={styles.msPrice}><span className={styles.msPriceInner}>{formatGold(l.price)}<img src={GOLD_ICON} alt="" width={12} height={12} /></span></td>
                    {!isGenericItem && (
                      <td className={styles.msStats}>
                        {l.properties.filter((p) => !p.is_primary).map((p, i) => (
                          <span key={i} className={styles.msStat}>{cleanStatName(p.property_type)}: {formatStatValue(p.property_type, p.property_value)}</span>
                        ))}
                        {l.properties.filter((p) => !p.is_primary).length === 0 && <span style={{ color: "var(--text-muted)" }}>—</span>}
                      </td>
                    )}
                    <td className={styles.msTime}>{l.sold_at ? timeAgo(l.sold_at) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
