"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import styles from "./market.module.css";
import { searchItems, type ItemDef } from "./api";

interface Props {
  onSelect: (item: { id: string; name: string }) => void;
}

export default function MarketSearch({ onSelect }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<ItemDef[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [searching, setSearching] = useState(false);

  const wrapperRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const doSearch = useCallback(
    (q: string) => {
      // Cancel previous request
      if (abortRef.current) abortRef.current.abort();

      if (q.trim().length < 2) {
        setResults([]);
        setShowDropdown(false);
        return;
      }

      const ac = new AbortController();
      abortRef.current = ac;
      setSearching(true);

      searchItems(q.trim(), 30, ac.signal)
        .then((items) => {
          if (!ac.signal.aborted) {
            // Deduplicate by archetype (same name across rarities)
            const seen = new Set<string>();
            const deduped: ItemDef[] = [];
            for (const item of items) {
              if (!seen.has(item.archetype)) {
                seen.add(item.archetype);
                deduped.push(item);
              }
            }
            setResults(deduped);
            setShowDropdown(deduped.length > 0);
            setSearching(false);
          }
        })
        .catch(() => {
          if (!ac.signal.aborted) {
            setSearching(false);
          }
        });
    },
    [],
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const val = e.target.value;
      setQuery(val);

      // Debounce 300ms
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => doSearch(val), 300);
    },
    [doSearch],
  );

  const handleSelect = useCallback(
    (item: ItemDef) => {
      onSelect({ id: item.id, name: item.name });
      setQuery("");
      setResults([]);
      setShowDropdown(false);
    },
    [onSelect],
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortRef.current) abortRef.current.abort();
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  return (
    <div className={styles.searchSection} ref={wrapperRef}>
      <span className={styles.searchIcon}>
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
      </span>
      <input
        type="text"
        className={styles.searchInput}
        placeholder="Search items..."
        value={query}
        onChange={handleChange}
        onFocus={() => {
          if (results.length > 0) setShowDropdown(true);
        }}
      />

      {showDropdown && results.length > 0 && (
        <div className={styles.searchResults}>
          {results.map((item) => (
            <div
              key={item.id}
              className={styles.searchResultItem}
              onClick={() => handleSelect(item)}
            >
              <span style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
                <img
                  src={"/item-icons/Item_Icon_" + item.archetype + ".png"}
                  width={24}
                  height={24}
                  alt=""
                  style={{ flexShrink: 0 }}
                  onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
                />
                <span className={styles.searchResultName}>{item.name}</span>
              </span>
              <span className={styles.searchResultRarity}>
                <RarityBadge rarity={item.rarity} />
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function RarityBadge({ rarity }: { rarity: string }) {
  const classMap: Record<string, string> = {
    Poor: styles.rarityPoor,
    Common: styles.rarityCommon,
    Uncommon: styles.rarityUncommon,
    Rare: styles.rarityRare,
    Epic: styles.rarityEpic,
    Legendary: styles.rarityLegendary,
    Unique: styles.rarityUnique,
    Artifact: styles.rarityArtifact,
  };

  return (
    <span className={classMap[rarity] ?? styles.rarityCommon}>
      {rarity}
    </span>
  );
}
