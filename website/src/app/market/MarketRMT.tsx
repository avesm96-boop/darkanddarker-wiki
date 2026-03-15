"use client";

import { useState, useEffect, useRef } from "react";
import styles from "./market.module.css";
import { fetchMarketListings, type MarketListing, itemIconPath, GOLD_ICON } from "./api";

interface FlaggedListing {
  listing: MarketListing;
  median: number;
  multiplier: number;
  reason: string;
  severity: "high" | "medium";
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function formatPrice(n: number): string {
  return Math.round(n).toLocaleString();
}

function GoldIcon() {
  return (
    <img src={GOLD_ICON} alt="" width={14} height={14}
      style={{ verticalAlign: "middle", marginRight: 2 }} />
  );
}

// Broad scan: fetch expensive listings, then verify each against same-item same-rarity median
async function scanMarket(signal: AbortSignal): Promise<FlaggedListing[]> {
  const flagged: FlaggedListing[] = [];
  const medianCache = new Map<string, number>(); // "item|rarity" → median

  // Phase 1: Fetch listings at different price thresholds to cast a wide net
  const thresholds = [
    { price: "50000:999999", label: ">50k" },
    { price: "20000:49999", label: "20k-50k" },
    { price: "10000:19999", label: "10k-20k" },
  ];

  const allSuspicious: MarketListing[] = [];

  for (const t of thresholds) {
    if (signal.aborted) break;
    try {
      const listings = await fetchMarketListings("", 50, true, signal, t.price);
      allSuspicious.push(...listings);
    } catch { /* ignore */ }
  }

  // Phase 2: For each suspicious listing, get the median for that item+rarity
  // Group by item name to batch API calls
  const itemGroups = new Map<string, MarketListing[]>();
  for (const l of allSuspicious) {
    const key = l.item;
    if (!itemGroups.has(key)) itemGroups.set(key, []);
    itemGroups.get(key)!.push(l);
  }

  // Fetch comparison listings for each unique item (max 5 concurrent)
  const itemNames = Array.from(itemGroups.keys());
  for (let i = 0; i < itemNames.length; i += 5) {
    if (signal.aborted) break;
    const batch = itemNames.slice(i, i + 5);
    const results = await Promise.all(
      batch.map(name =>
        fetchMarketListings(name, 50, true, signal)
          .then(listings => ({ name, listings }))
          .catch(() => ({ name, listings: [] as MarketListing[] }))
      )
    );

    for (const { name, listings } of results) {
      if (listings.length < 3) continue;

      // Group by rarity to get per-rarity medians
      const byRarity = new Map<string, number[]>();
      for (const l of listings) {
        if (l.price_per_unit <= 0) continue;
        const r = l.rarity;
        if (!byRarity.has(r)) byRarity.set(r, []);
        byRarity.get(r)!.push(l.price_per_unit);
      }

      for (const [rarity, prices] of byRarity) {
        prices.sort((a, b) => a - b);
        const median = prices[Math.floor(prices.length / 2)];
        medianCache.set(`${name}|${rarity}`, median);
      }

      // Now check each suspicious listing for this item
      const suspects = itemGroups.get(name) ?? [];
      for (const listing of suspects) {
        const cacheKey = `${listing.item}|${listing.rarity}`;
        const median = medianCache.get(cacheKey);
        if (!median || median <= 0) continue;

        const ppu = listing.price_per_unit;
        const multiplier = ppu / median;

        if (multiplier >= 50) {
          flagged.push({
            listing,
            median,
            multiplier,
            reason: `${formatPrice(ppu)}g per unit is ${Math.round(multiplier)}x the typical ${listing.rarity} price of ~${formatPrice(median)}g. Almost certainly RMT gold transfer.`,
            severity: "high",
          });
        } else if (multiplier >= 15) {
          flagged.push({
            listing,
            median,
            multiplier,
            reason: `${formatPrice(ppu)}g per unit is ${Math.round(multiplier)}x the typical ${listing.rarity} price of ~${formatPrice(median)}g. Highly suspicious pricing.`,
            severity: "high",
          });
        } else if (multiplier >= 5) {
          flagged.push({
            listing,
            median,
            multiplier,
            reason: `${formatPrice(ppu)}g per unit is ${multiplier.toFixed(1)}x the typical ${listing.rarity} price of ~${formatPrice(median)}g. Possibly overpriced or RMT.`,
            severity: "medium",
          });
        }
        // Below 5x — could be legit (good rolls, unique stats)
      }
    }
  }

  // Sort: high severity first, then by multiplier descending
  flagged.sort((a, b) => {
    if (a.severity !== b.severity) return a.severity === "high" ? -1 : 1;
    return b.multiplier - a.multiplier;
  });

  return flagged;
}

export default function MarketRMT() {
  const [flagged, setFlagged] = useState<FlaggedListing[]>([]);
  const [loading, setLoading] = useState(true);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (abortRef.current) abortRef.current.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setLoading(true);

    scanMarket(ac.signal)
      .then(results => {
        if (!ac.signal.aborted) {
          setFlagged(results);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!ac.signal.aborted) setLoading(false);
      });

    return () => ac.abort();
  }, []);

  return (
    <div className={styles.dashboard}>
      <div className={styles.sectionHeader}>
        <span className={styles.sectionTitle}>
          Suspicious Listings Scanner
        </span>
      </div>

      <p style={{
        fontSize: "0.75rem", color: "var(--text-muted)",
        marginBottom: 16, lineHeight: 1.6,
      }}>
        We scan the entire marketplace for listings priced dramatically higher than
        the typical price for that item and rarity. These are often RMT (real money trading)
        gold transfers — a player lists a cheap item at an absurd price so another account can
        &quot;buy&quot; it to transfer gold. Only listings at 5x+ the typical same-rarity price are shown.
      </p>

      {loading && (
        <div style={{ color: "var(--gold-500)", fontSize: "0.8125rem", padding: "20px 0" }}>
          Scanning marketplace for suspicious activity...
        </div>
      )}

      {!loading && flagged.length === 0 && (
        <div style={{ color: "var(--text-muted)", fontSize: "0.8125rem", padding: "20px 0" }}>
          No suspicious listings found right now. The marketplace looks clean.
        </div>
      )}

      {!loading && flagged.length > 0 && (
        <>
          <div style={{
            fontSize: "0.75rem", color: "var(--gold-500)",
            marginBottom: 12,
          }}>
            Found {flagged.length} suspicious listing{flagged.length !== 1 ? "s" : ""}
          </div>

          <div className={styles.trendTable}>
            <div className={styles.rmtTableHeader}>
              <span></span>
              <span>Item</span>
              <span>Rarity</span>
              <span>Listed Price</span>
              <span>Qty</span>
              <span>Typical Price</span>
              <span>Markup</span>
              <span>Severity</span>
            </div>
            {flagged.slice(0, 100).map((f, idx) => (
              <div key={idx} className={styles.rmtTableRow}>
                <span>
                  <img
                    src={itemIconPath(f.listing.archetype)}
                    alt="" width={28} height={28}
                    className={styles.itemIcon}
                    onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                  />
                </span>
                <span className={styles.trendItemName}>
                  {f.listing.item}
                </span>
                <span>
                  <span className={styles[`rarity${f.listing.rarity}`] ?? styles.rarityCommon}>
                    {f.listing.rarity}
                  </span>
                </span>
                <span className={styles.priceCell}>
                  <GoldIcon />{formatPrice(f.listing.price_per_unit)}
                </span>
                <span style={{ color: "var(--text-muted)", fontSize: "0.75rem", fontVariantNumeric: "tabular-nums" }}>
                  {f.listing.quantity}
                </span>
                <span className={styles.priceCell}>
                  <GoldIcon />{formatPrice(f.median)}
                </span>
                <span style={{
                  color: f.multiplier >= 15 ? "#e05555" : "var(--gold-500)",
                  fontSize: "0.75rem", fontWeight: 600, fontVariantNumeric: "tabular-nums",
                }}>
                  {Math.round(f.multiplier)}x
                </span>
                <span className={f.severity === "high" ? styles.rmtHigh : styles.rmtMedium}>
                  {f.severity === "high" ? "HIGH" : "MEDIUM"}
                </span>
              </div>
            ))}
          </div>

          {flagged.length > 100 && (
            <p style={{ color: "var(--text-muted)", fontSize: "0.6875rem", marginTop: 8, fontStyle: "italic" }}>
              Showing top 100 of {flagged.length} suspicious listings.
            </p>
          )}

          {/* Reasoning for top entries */}
          <div style={{ marginTop: 16 }}>
            <div className={styles.sectionHeader}>
              <span className={styles.sectionTitle}>Detection Reasoning (Top 20)</span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {flagged.slice(0, 20).map((f, idx) => (
                <div key={idx} style={{
                  fontSize: "0.6875rem",
                  padding: "8px 12px",
                  background: f.severity === "high"
                    ? "rgba(220, 50, 50, 0.06)"
                    : "rgba(201, 168, 76, 0.04)",
                  border: `1px solid ${f.severity === "high"
                    ? "rgba(220, 50, 50, 0.15)"
                    : "var(--border-dim)"}`,
                  borderRadius: 6,
                  color: "var(--text-dim)",
                  lineHeight: 1.5,
                }}>
                  <strong style={{ color: f.severity === "high" ? "#e05555" : "var(--gold-500)" }}>
                    {f.listing.item} ({f.listing.rarity})
                  </strong>
                  {" — "}{f.reason}
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      <div style={{
        fontSize: "0.6875rem", color: "var(--text-muted)",
        fontStyle: "italic", marginTop: 20, opacity: 0.7, lineHeight: 1.7,
      }}>
        <p>
          <strong style={{ color: "var(--gold-500)", fontStyle: "normal" }}>How it works:</strong>{" "}
          We fetch all marketplace listings above 10,000g, then compare each one to the median
          price of the same item at the same rarity. A Unique Longsword at 15,000g might be
          perfectly normal, but a Common Longsword at 15,000g (when typical is 200g) is 75x markup
          — almost certainly a gold transfer.
        </p>
        <p style={{ marginTop: 8 }}>
          <strong style={{ color: "var(--gold-500)", fontStyle: "normal" }}>Disclaimer:</strong>{" "}
          This is automated detection based on price anomalies. Not all flagged listings are RMT —
          some may be pricing mistakes, items with exceptional stats, or intentional overpricing.
          Seller names are not available through the API.
        </p>
      </div>
    </div>
  );
}
