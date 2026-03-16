"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import styles from "./market.module.css";
import { searchItems, fetchRawListings, GOLD_ICON, itemIconPath, type ItemDef, type RawListing } from "./api";

const BASE_RARITIES = ["Poor", "Common", "Uncommon", "Rare", "Epic", "Legendary", "Unique", "Artifact"];

function cleanPropName(raw: string): string {
  return raw
    .replace("Id_ItemPropertyType_Effect_", "")
    .replace(/([A-Z])/g, " $1")
    .trim();
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

interface PropertyFilter {
  name: string;  // raw property_type
  label: string; // cleaned display name
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
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  // Available properties (discovered from results)
  const [availableProps, setAvailableProps] = useState<string[]>([]);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  // Close suggestions on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  // Autocomplete search
  const handleQueryChange = useCallback((val: string) => {
    setQuery(val);
    setSelectedItem(null);

    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (val.trim().length < 2) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    debounceRef.current = setTimeout(() => {
      const ac = new AbortController();
      searchItems(val.trim(), 20, ac.signal)
        .then((items) => {
          const seen = new Set<string>();
          const deduped = items.filter((i) => {
            if (seen.has(i.archetype)) return false;
            seen.add(i.archetype);
            return true;
          });
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

    try {
      const [active, sold] = await Promise.all([
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
      ]);

      if (!ac.signal.aborted) {
        setActiveListings(active);
        setSoldListings(sold);

        // Discover available secondary properties from results
        const propSet = new Set<string>();
        for (const l of active) {
          for (const p of l.properties) {
            if (!p.is_primary) propSet.add(p.property_type);
          }
        }
        setAvailableProps(Array.from(propSet).sort());
        setLoading(false);
      }
    } catch {
      if (!ac.signal.aborted) setLoading(false);
    }
  }, [selectedItem, selectedRarity]);

  // Apply client-side property filters
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
    setPropFilters([...propFilters, { name: propName, label: cleanPropName(propName), min: 1 }]);
  };

  const removePropFilter = (propName: string) => {
    setPropFilters(propFilters.filter((f) => f.name !== propName));
  };

  const updatePropFilterMin = (propName: string, min: number) => {
    setPropFilters(propFilters.map((f) => f.name === propName ? { ...f, min } : f));
  };

  // Enter key triggers search
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && selectedItem) doSearch();
  };

  return (
    <div className={styles.dashboard}>
      <div className={styles.sectionHeader}>
        <span className={styles.sectionTitle}>Market Search</span>
      </div>

      {/* Search Form */}
      <div className={styles.msForm}>
        {/* Item Name */}
        <div className={styles.msField} ref={wrapperRef}>
          <label className={styles.msLabel}>Item</label>
          <div style={{ position: "relative" }}>
            <input
              type="text"
              className={styles.msInput}
              placeholder="Search item name..."
              value={query}
              onChange={(e) => handleQueryChange(e.target.value)}
              onFocus={() => { if (suggestions.length > 0) setShowSuggestions(true); }}
              onKeyDown={handleKeyDown}
            />
            {showSuggestions && suggestions.length > 0 && (
              <div className={styles.msSuggestions}>
                {suggestions.map((item) => (
                  <div
                    key={item.id}
                    className={styles.msSuggestionItem}
                    onClick={() => handleSelectItem(item)}
                  >
                    <img
                      src={itemIconPath(item.archetype)}
                      width={20} height={20} alt=""
                      onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                    />
                    <span>{item.name}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Rarity */}
        <div className={styles.msField}>
          <label className={styles.msLabel}>Rarity</label>
          <select
            className={styles.msSelect}
            value={selectedRarity}
            onChange={(e) => setSelectedRarity(e.target.value)}
          >
            <option value="">All Rarities</option>
            {BASE_RARITIES.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </div>

        {/* Search Button */}
        <div className={styles.msField} style={{ alignSelf: "flex-end" }}>
          <button
            className={styles.msSearchBtn}
            onClick={doSearch}
            disabled={!selectedItem || loading}
          >
            {loading ? "Searching..." : "Search"}
          </button>
        </div>
      </div>

      {/* Attribute Filters (appear after search) */}
      {searched && availableProps.length > 0 && (
        <div className={styles.msAttrFilters}>
          <div className={styles.msAttrHeader}>
            <span className={styles.msLabel}>Filter by Stats</span>
            <select
              className={styles.msSelect}
              value=""
              onChange={(e) => { if (e.target.value) addPropFilter(e.target.value); e.target.value = ""; }}
              style={{ maxWidth: 200 }}
            >
              <option value="">+ Add attribute...</option>
              {availableProps
                .filter((p) => !propFilters.some((f) => f.name === p))
                .map((p) => (
                  <option key={p} value={p}>{cleanPropName(p)}</option>
                ))}
            </select>
          </div>
          {propFilters.length > 0 && (
            <div className={styles.msAttrList}>
              {propFilters.map((f) => (
                <div key={f.name} className={styles.msAttrChip}>
                  <span>{f.label} ≥</span>
                  <input
                    type="number"
                    className={styles.msAttrInput}
                    value={f.min}
                    onChange={(e) => updatePropFilterMin(f.name, parseInt(e.target.value) || 0)}
                    min={0}
                  />
                  <button className={styles.msAttrRemove} onClick={() => removePropFilter(f.name)}>×</button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Active Listings */}
      {searched && (
        <div style={{ marginTop: 24 }}>
          <div className={styles.sectionHeader}>
            <span className={styles.sectionTitle}>
              Active Listings ({filteredActive.length}{propFilters.length > 0 ? ` of ${activeListings.length}` : ""})
            </span>
          </div>
          {filteredActive.length === 0 ? (
            <div className={styles.msEmpty}>
              {loading ? "Loading..." : "No listings found matching your criteria."}
            </div>
          ) : (
            <div className={styles.msTableWrap}>
              <table className={styles.msTable}>
                <thead>
                  <tr>
                    <th>Price</th>
                    <th>Rarity</th>
                    <th>Stats</th>
                    <th>Seller</th>
                    <th>Listed</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredActive.slice(0, 50).map((l) => (
                    <tr key={l.listing_id}>
                      <td className={styles.msPrice}>
                        {formatGold(l.price)}
                        <img src={GOLD_ICON} alt="" width={12} height={12} />
                      </td>
                      <td><span className={styles[`rarity${l.base_rarity}`] || ""}>{l.base_rarity}</span></td>
                      <td className={styles.msStats}>
                        {l.properties
                          .filter((p) => !p.is_primary)
                          .map((p, i) => (
                            <span key={i} className={styles.msStat}>
                              {cleanPropName(p.property_type)}: {p.property_value}
                            </span>
                          ))}
                        {l.properties.filter((p) => !p.is_primary).length === 0 && "—"}
                      </td>
                      <td className={styles.msSeller}>{l.seller_name || "Anonymous"}</td>
                      <td className={styles.msTime}>{timeAgo(l.first_seen_at)}</td>
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
      {searched && filteredSold.length > 0 && (
        <div style={{ marginTop: 32 }}>
          <div className={styles.sectionHeader}>
            <span className={styles.sectionTitle}>Recently Sold (Last 10)</span>
          </div>
          <div className={styles.msTableWrap}>
            <table className={styles.msTable}>
              <thead>
                <tr>
                  <th>Sale Price</th>
                  <th>Rarity</th>
                  <th>Stats</th>
                  <th>Sold</th>
                </tr>
              </thead>
              <tbody>
                {filteredSold.map((l) => (
                  <tr key={l.listing_id} className={styles.msSoldRow}>
                    <td className={styles.msPrice}>
                      {formatGold(l.price)}
                      <img src={GOLD_ICON} alt="" width={12} height={12} />
                    </td>
                    <td><span className={styles[`rarity${l.base_rarity}`] || ""}>{l.base_rarity}</span></td>
                    <td>{l.rarity_name === "None" ? "—" : l.rarity_name}</td>
                    <td className={styles.msStats}>
                      {l.properties
                        .filter((p) => !p.is_primary)
                        .map((p, i) => (
                          <span key={i} className={styles.msStat}>
                            {cleanPropName(p.property_type)}: {p.property_value}
                          </span>
                        ))}
                      {l.properties.filter((p) => !p.is_primary).length === 0 && "—"}
                    </td>
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
