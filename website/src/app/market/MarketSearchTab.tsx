"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import styles from "./market.module.css";
import { searchItems, fetchRawListings, fetchPriceHistory, GOLD_ICON, itemIconPath, type ItemDef, type RawListing, type PricePoint } from "./api";
import ItemTooltip from "./ItemTooltip";
import { cleanStatName, formatStatValue } from "./statFormat";
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid, BarChart, Bar } from "recharts";

const BASE_RARITIES = ["Poor", "Common", "Uncommon", "Rare", "Epic", "Legendary", "Unique", "Artifact"];

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

function formatShortDate(ts: string): string {
  const d = new Date(ts);
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, "0")}`;
}

interface PropertyFilter {
  name: string;
  label: string;
  min: number;
}

export default function MarketSearchTab() {
  // Search form state
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<ItemDef[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedItem, setSelectedItem] = useState<{ id: string; name: string; archetype: string } | null>(null);
  const [selectedRarity, setSelectedRarity] = useState("");
  const [propFilters, setPropFilters] = useState<PropertyFilter[]>([]);

  // Results state
  const [activeListings, setActiveListings] = useState<RawListing[]>([]);
  const [soldListings, setSoldListings] = useState<RawListing[]>([]);
  const [priceHistory, setPriceHistory] = useState<PricePoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [previewListing, setPreviewListing] = useState<RawListing | null>(null);
  const [chartTimeframe, setChartTimeframe] = useState<"1d" | "4h" | "1h">("4h");

  // Is this item an "Unknown" rarity item (consumable/material)?
  const [isGenericItem, setIsGenericItem] = useState(false);

  // Available properties
  const [availableProps, setAvailableProps] = useState<string[]>([]);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

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
          const deduped = items.filter((i) => { if (seen.has(i.archetype)) return false; seen.add(i.archetype); return true; });
          setSuggestions(deduped);
          setShowSuggestions(deduped.length > 0);
        })
        .catch(() => {});
    }, 250);
  }, []);

  const handleSelectItem = useCallback((item: ItemDef) => {
    setSelectedItem({ id: item.id, name: item.name, archetype: item.archetype });
    setQuery(item.name);
    setShowSuggestions(false);
    setSuggestions([]);
  }, []);

  // Execute search
  const doSearch = useCallback(async () => {
    if (!selectedItem) return;
    if (abortRef.current) abortRef.current.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setLoading(true);
    setSearched(true);
    setPreviewListing(null);

    try {
      const [active, sold, history] = await Promise.all([
        fetchRawListings(selectedItem.archetype, {
          base_rarity: selectedRarity || undefined,
          status: "active",
          limit: 500,
          sort: "price_asc",
        }, ac.signal),
        fetchRawListings(selectedItem.archetype, {
          base_rarity: selectedRarity || undefined,
          status: "sold",
          limit: 100,
          sort: "sold_desc",
        }, ac.signal),
        fetchPriceHistory(selectedItem.archetype, chartTimeframe === "1d" ? "1d" : chartTimeframe === "4h" ? "4h" : "1h", ac.signal),
      ]);

      if (!ac.signal.aborted) {
        setActiveListings(active);
        setSoldListings(sold);
        setPriceHistory(history);

        // Detect if this is a generic item (Unknown rarity = consumable/material)
        const hasUnknown = active.length > 0 && active.every((l) => l.base_rarity === "Unknown");
        setIsGenericItem(hasUnknown);

        const propSet = new Set<string>();
        for (const l of active) {
          for (const p of l.properties) { if (!p.is_primary) propSet.add(p.property_type); }
        }
        setAvailableProps(Array.from(propSet).sort());
        setLoading(false);
      }
    } catch {
      if (!ac.signal.aborted) setLoading(false);
    }
  }, [selectedItem, selectedRarity, chartTimeframe]);

  // Reload price history when timeframe changes
  useEffect(() => {
    if (!searched || !selectedItem) return;
    const ac = new AbortController();
    fetchPriceHistory(selectedItem.archetype, chartTimeframe === "1d" ? "1d" : chartTimeframe === "4h" ? "4h" : "1h", ac.signal)
      .then((h) => { if (!ac.signal.aborted) setPriceHistory(h); })
      .catch(() => {});
    return () => ac.abort();
  }, [chartTimeframe, searched, selectedItem]);

  // Filters
  const applyPropFilters = (listing: RawListing) => {
    for (const f of propFilters) {
      const prop = listing.properties.find((p) => p.property_type === f.name && !p.is_primary);
      if (!prop || prop.property_value < f.min) return false;
    }
    return true;
  };
  const filteredActive = activeListings.filter(applyPropFilters);
  const filteredSold = soldListings.filter(applyPropFilters).slice(0, 10);

  const addPropFilter = (propName: string) => {
    if (propFilters.some((f) => f.name === propName)) return;
    setPropFilters([...propFilters, { name: propName, label: cleanStatName(propName), min: 1 }]);
  };
  const removePropFilter = (propName: string) => { setPropFilters(propFilters.filter((f) => f.name !== propName)); };
  const updatePropFilterMin = (propName: string, min: number) => {
    setPropFilters(propFilters.map((f) => f.name === propName ? { ...f, min } : f));
  };
  const handleKeyDown = (e: React.KeyboardEvent) => { if (e.key === "Enter" && selectedItem) doSearch(); };

  // Compute average prices from sold listings
  const now = Date.now() / 1000;
  const soldPrices24h = soldListings.filter((l) => l.sold_at && l.sold_at > now - 86400).map((l) => l.price / Math.max(l.item_count, 1));
  const soldPrices7d = soldListings.filter((l) => l.sold_at && l.sold_at > now - 7 * 86400).map((l) => l.price / Math.max(l.item_count, 1));
  const soldPrices14d = soldListings.map((l) => l.price / Math.max(l.item_count, 1));
  const avg = (arr: number[]) => arr.length ? Math.round(arr.reduce((a, b) => a + b, 0) / arr.length) : 0;

  return (
    <div className={styles.dashboard}>
      <div className={styles.sectionHeader}>
        <span className={styles.sectionTitle}>Market Search</span>
      </div>

      {/* Search Form */}
      <div className={styles.msForm}>
        <div className={styles.msField} ref={wrapperRef}>
          <label className={styles.msLabel}>Item</label>
          <div style={{ position: "relative" }}>
            <input type="text" className={styles.msInput} placeholder="Search item name..." value={query}
              onChange={(e) => handleQueryChange(e.target.value)}
              onFocus={() => { if (suggestions.length > 0) setShowSuggestions(true); }}
              onKeyDown={handleKeyDown} />
            {showSuggestions && suggestions.length > 0 && (
              <div className={styles.msSuggestions}>
                {suggestions.map((item) => (
                  <div key={item.id} className={styles.msSuggestionItem} onClick={() => handleSelectItem(item)}>
                    <img src={itemIconPath(item.archetype)} width={20} height={20} alt=""
                      onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
                    <span>{item.name}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Rarity — hide for generic items */}
        <div className={styles.msField}>
          <label className={styles.msLabel}>Rarity</label>
          <select className={styles.msSelect} value={selectedRarity} onChange={(e) => setSelectedRarity(e.target.value)}>
            <option value="">All Rarities</option>
            {BASE_RARITIES.map((r) => (<option key={r} value={r}>{r}</option>))}
          </select>
        </div>

        <div className={styles.msField} style={{ alignSelf: "flex-end" }}>
          <button className={styles.msSearchBtn} onClick={doSearch} disabled={!selectedItem || loading}>
            {loading ? "Searching..." : "Search"}
          </button>
        </div>
      </div>

      {/* Price Analytics — for generic items (consumables/materials) */}
      {searched && isGenericItem && (
        <div style={{ marginTop: 16 }}>
          {/* Average Price Cards */}
          <div className={styles.dashboardGrid} style={{ marginBottom: 20 }}>
            <div className={styles.statCard}>
              <div className={styles.statValue}>{avg(soldPrices14d) ? formatGold(avg(soldPrices14d)) : "—"}</div>
              <div className={styles.statLabel}>Avg Price 14D</div>
            </div>
            <div className={styles.statCard}>
              <div className={styles.statValue}>{avg(soldPrices7d) ? formatGold(avg(soldPrices7d)) : "—"}</div>
              <div className={styles.statLabel}>Avg Price 7D</div>
            </div>
            <div className={styles.statCard}>
              <div className={styles.statValue}>{avg(soldPrices24h) ? formatGold(avg(soldPrices24h)) : "—"}</div>
              <div className={styles.statLabel}>Avg Price 24H</div>
            </div>
          </div>

          {/* Chart Timeframe Toggle */}
          <div style={{ display: "flex", gap: 6, marginBottom: 12 }}>
            {(["1h", "4h", "1d"] as const).map((tf) => (
              <button key={tf} className={chartTimeframe === tf ? styles.classBtnActive : styles.classBtn}
                onClick={() => setChartTimeframe(tf)}
                style={{ padding: "4px 12px", fontSize: "0.7rem" }}>
                {tf === "1h" ? "24H" : tf === "4h" ? "7D" : "14D"}
              </button>
            ))}
          </div>

          {/* Price Chart */}
          {priceHistory.length > 1 && (
            <div style={{ marginBottom: 24 }}>
              <div className={styles.sectionHeader}>
                <span className={styles.sectionTitle}>Price Chart</span>
              </div>
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={priceHistory}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(201,168,76,0.1)" />
                  <XAxis dataKey="timestamp" tickFormatter={formatShortDate} tick={{ fontSize: 10, fill: "#888" }} />
                  <YAxis tick={{ fontSize: 10, fill: "#888" }} />
                  <Tooltip
                    contentStyle={{ background: "#1a1816", border: "1px solid rgba(201,168,76,0.3)", fontSize: "0.75rem" }}
                    labelFormatter={(label) => formatShortDate(String(label))}
                    formatter={(value) => [formatGold(Number(value)) + "g", ""]}
                  />
                  <Area type="monotone" dataKey="avg" stroke="rgba(201,168,76,0.8)" fill="rgba(201,168,76,0.15)" strokeWidth={2} name="Avg Price" />
                  <Area type="monotone" dataKey="min" stroke="rgba(76,201,100,0.5)" fill="none" strokeWidth={1} strokeDasharray="3 3" name="Min" />
                  <Area type="monotone" dataKey="max" stroke="rgba(224,85,85,0.5)" fill="none" strokeWidth={1} strokeDasharray="3 3" name="Max" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Demand Chart */}
          {priceHistory.length > 1 && (
            <div style={{ marginBottom: 24 }}>
              <div className={styles.sectionHeader}>
                <span className={styles.sectionTitle}>Demand (Active Listings)</span>
              </div>
              <ResponsiveContainer width="100%" height={150}>
                <BarChart data={priceHistory}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(201,168,76,0.1)" />
                  <XAxis dataKey="timestamp" tickFormatter={formatShortDate} tick={{ fontSize: 10, fill: "#888" }} />
                  <YAxis tick={{ fontSize: 10, fill: "#888" }} />
                  <Tooltip
                    contentStyle={{ background: "#1a1816", border: "1px solid rgba(201,168,76,0.3)", fontSize: "0.75rem" }}
                    labelFormatter={(label) => formatShortDate(String(label))}
                  />
                  <Bar dataKey="volume" fill="rgba(201,168,76,0.4)" name="Active Listings" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}

      {/* Attribute Filters */}
      {searched && availableProps.length > 0 && !isGenericItem && (
        <div className={styles.msAttrFilters}>
          <div className={styles.msAttrHeader}>
            <span className={styles.msLabel}>Filter by Stats</span>
            <select className={styles.msSelect} value=""
              onChange={(e) => { if (e.target.value) addPropFilter(e.target.value); e.target.value = ""; }}
              style={{ maxWidth: 200 }}>
              <option value="">+ Add attribute...</option>
              {availableProps.filter((p) => !propFilters.some((f) => f.name === p)).map((p) => (
                <option key={p} value={p}>{cleanStatName(p)}</option>
              ))}
            </select>
          </div>
          {propFilters.length > 0 && (
            <div className={styles.msAttrList}>
              {propFilters.map((f) => (
                <div key={f.name} className={styles.msAttrChip}>
                  <span>{f.label} ≥</span>
                  <input type="number" className={styles.msAttrInput} value={f.min}
                    onChange={(e) => updatePropFilterMin(f.name, parseInt(e.target.value) || 0)} min={0} />
                  <button className={styles.msAttrRemove} onClick={() => removePropFilter(f.name)}>×</button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Item Preview Card */}
      {previewListing && selectedItem && (
        <div style={{ display: "flex", justifyContent: "center", margin: "20px 0" }}>
          <ItemTooltip itemName={selectedItem.name} rarity={previewListing.base_rarity} properties={previewListing.properties} />
        </div>
      )}

      {/* Active Listings Table */}
      {searched && (
        <div style={{ marginTop: 24 }}>
          <div className={styles.sectionHeader}>
            <span className={styles.sectionTitle}>
              Active Listings ({filteredActive.length}{propFilters.length > 0 ? ` of ${activeListings.length}` : ""})
            </span>
          </div>
          {filteredActive.length === 0 ? (
            <div className={styles.msEmpty}>{loading ? "Loading..." : "No listings found matching your criteria."}</div>
          ) : (
            <div className={styles.msTableWrap}>
              <table className={styles.msTable}>
                <thead>
                  <tr>
                    <th>Price</th>
                    {!isGenericItem && <th>Rarity</th>}
                    {!isGenericItem && <th>Stats</th>}
                    <th>{isGenericItem ? "Qty" : "Listed"}</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredActive.slice(0, 50).map((l) => (
                    <tr key={l.listing_id}
                      onClick={() => !isGenericItem && setPreviewListing(previewListing?.listing_id === l.listing_id ? null : l)}
                      style={!isGenericItem ? { cursor: "pointer" } : undefined}
                      className={previewListing?.listing_id === l.listing_id ? styles.msSelectedRow : ""}>
                      <td className={styles.msPrice}>
                        {formatGold(l.price)}<img src={GOLD_ICON} alt="" width={12} height={12} />
                      </td>
                      {!isGenericItem && <td><span className={styles[`rarity${l.base_rarity}`] || ""}>{l.base_rarity}</span></td>}
                      {!isGenericItem && (
                        <td className={styles.msStats}>
                          {l.properties.filter((p) => !p.is_primary).map((p, i) => (
                            <span key={i} className={styles.msStat}>
                              {cleanStatName(p.property_type)}: {formatStatValue(p.property_type, p.property_value)}
                            </span>
                          ))}
                          {l.properties.filter((p) => !p.is_primary).length === 0 && "—"}
                        </td>
                      )}
                      <td className={styles.msTime}>{isGenericItem ? l.item_count : timeAgo(l.first_seen_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {filteredActive.length > 50 && (
                <div className={styles.msEmpty} style={{ padding: 8 }}>
                  Showing 50 of {filteredActive.length} — refine filters to see more specific results.
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Recently Sold */}
      {searched && soldListings.length > 0 && (
        <div style={{ marginTop: 32 }}>
          <div className={styles.sectionHeader}>
            <span className={styles.sectionTitle}>Recently Sold (Last 10)</span>
          </div>
          <div className={styles.msTableWrap}>
            <table className={styles.msTable}>
              <thead>
                <tr>
                  <th>Sale Price</th>
                  {!isGenericItem && <th>Rarity</th>}
                  {!isGenericItem && <th>Stats</th>}
                  <th>Sold</th>
                </tr>
              </thead>
              <tbody>
                {filteredSold.length === 0 ? (
                  <tr><td colSpan={isGenericItem ? 2 : 4} className={styles.msEmpty}>No sold items match the current filters.</td></tr>
                ) : (
                  filteredSold.map((l) => (
                    <tr key={l.listing_id} className={styles.msSoldRow}>
                      <td className={styles.msPrice}>
                        {formatGold(l.price)}<img src={GOLD_ICON} alt="" width={12} height={12} />
                      </td>
                      {!isGenericItem && <td><span className={styles[`rarity${l.base_rarity}`] || ""}>{l.base_rarity}</span></td>}
                      {!isGenericItem && (
                        <td className={styles.msStats}>
                          {l.properties.filter((p) => !p.is_primary).map((p, i) => (
                            <span key={i} className={styles.msStat}>
                              {cleanStatName(p.property_type)}: {formatStatValue(p.property_type, p.property_value)}
                            </span>
                          ))}
                          {l.properties.filter((p) => !p.is_primary).length === 0 && "—"}
                        </td>
                      )}
                      <td className={styles.msTime}>{l.sold_at ? timeAgo(l.sold_at) : "—"}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
