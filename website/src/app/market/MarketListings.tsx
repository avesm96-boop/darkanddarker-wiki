"use client";

import { useState, useEffect, useRef } from "react";
import styles from "./market.module.css";
import { fetchMarketListings, type MarketListing } from "./api";

interface Props {
  itemName: string;
}

/** Known listing keys that are NOT dynamic stat properties. */
const KNOWN_KEYS = new Set([
  "id", "cursor", "item_id", "item", "archetype", "rarity",
  "price", "price_per_unit", "quantity", "created_at", "expires_at",
  "has_sold", "has_expired", "seller",
]);

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function formatStatKey(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function getRarityClass(rarity: string): string {
  const map: Record<string, string> = {
    Poor: styles.rarityPoor,
    Common: styles.rarityCommon,
    Uncommon: styles.rarityUncommon,
    Rare: styles.rarityRare,
    Epic: styles.rarityEpic,
    Legendary: styles.rarityLegendary,
    Unique: styles.rarityUnique,
    Artifact: styles.rarityArtifact,
  };
  return map[rarity] ?? styles.rarityCommon;
}

function extractProperties(listing: MarketListing): string {
  const props: string[] = [];
  for (const [key, value] of Object.entries(listing)) {
    if (KNOWN_KEYS.has(key)) continue;
    if (value === null || value === undefined || value === 0 || value === "") continue;
    props.push(`${formatStatKey(key)}: ${value}`);
  }
  return props.join(", ") || "\u2014";
}

export default function MarketListings({ itemName }: Props) {
  const [listings, setListings] = useState<MarketListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  // Initial load
  useEffect(() => {
    if (abortRef.current) abortRef.current.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setLoading(true);
    setListings([]);

    fetchMarketListings(itemName, 25, true, ac.signal)
      .then((items) => {
        if (!ac.signal.aborted) {
          setListings(items);
          setHasMore(items.length >= 25);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!ac.signal.aborted) {
          setListings([]);
          setLoading(false);
        }
      });

    return () => ac.abort();
  }, [itemName]);

  const loadMore = () => {
    if (loadingMore || listings.length === 0) return;

    const ac = new AbortController();
    abortRef.current = ac;
    setLoadingMore(true);

    // Use last cursor for pagination
    const lastCursor = listings[listings.length - 1]?.cursor;

    fetchMarketListings(itemName, 25, true, ac.signal)
      .then((items) => {
        if (!ac.signal.aborted) {
          // Filter out duplicates by id
          const existingIds = new Set(listings.map((l) => l.id));
          const newItems = items.filter((l) => !existingIds.has(l.id));
          setListings((prev) => [...prev, ...newItems]);
          setHasMore(items.length >= 25);
          setLoadingMore(false);
        }
      })
      .catch(() => {
        if (!ac.signal.aborted) {
          setLoadingMore(false);
        }
      });
  };

  // Loading skeleton
  if (loading) {
    return (
      <div className={styles.listingsSection}>
        <h3 className={styles.listingsTitle}>Active Listings</h3>
        <div style={{ background: "var(--glass-bg)", borderRadius: 10, border: "1px solid var(--border-dim)" }}>
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className={styles.skeletonRow}>
              <div className={styles.skeletonBar} style={{ width: "15%", height: 12 }} />
              <div className={styles.skeletonBar} style={{ width: "20%", height: 12 }} />
              <div className={styles.skeletonBar} style={{ width: "10%", height: 12 }} />
              <div className={styles.skeletonBar} style={{ width: "15%", height: 12 }} />
              <div className={styles.skeletonBar} style={{ width: "30%", height: 12 }} />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (listings.length === 0) {
    return (
      <div className={styles.listingsSection}>
        <h3 className={styles.listingsTitle}>Active Listings</h3>
        <div className={styles.listingsEmpty}>No active listings found.</div>
      </div>
    );
  }

  return (
    <div className={styles.listingsSection}>
      <h3 className={styles.listingsTitle}>Active Listings</h3>
      <table className={styles.listingsTable}>
        <thead>
          <tr className={styles.listingsHeader}>
            <th>Rarity</th>
            <th>Price</th>
            <th>Qty</th>
            <th>Listed</th>
            <th>Properties</th>
          </tr>
        </thead>
        <tbody>
          {listings.map((listing) => (
            <tr key={listing.id} className={styles.listingsRow}>
              <td>
                <span className={getRarityClass(listing.rarity)}>
                  {listing.rarity}
                </span>
              </td>
              <td>{listing.price.toLocaleString()}g</td>
              <td>{listing.quantity}</td>
              <td>{timeAgo(listing.created_at)}</td>
              <td>{extractProperties(listing)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {hasMore && (
        <button
          className={styles.loadMoreBtn}
          onClick={loadMore}
          disabled={loadingMore}
        >
          {loadingMore ? "Loading..." : "Load More"}
        </button>
      )}
    </div>
  );
}
