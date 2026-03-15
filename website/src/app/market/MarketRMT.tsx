"use client";

import { useState, useEffect, useRef } from "react";
import styles from "./market.module.css";
import { fetchMarketListings, type MarketListing, itemIconPath, GOLD_ICON } from "./api";

// Items commonly used for RMT gold transfers + high-value items prone to manipulation
const SCAN_ITEMS = [
  "Silver Coin", "Gold Coin Purse", "Gold Coin Bag", "Golden Teeth",
  "Wolf Pelt", "Bone Powder", "Shining Pearl", "Lockpick",
  "Rotten Fluids", "Wolf Claw", "Gold Ingot", "Ruby",
  "Diamond", "Surgical Kit", "Bandage", "Ale",
];

interface FlaggedListing {
  listing: MarketListing;
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

export default function MarketRMT() {
  const [flagged, setFlagged] = useState<FlaggedListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanned, setScanned] = useState(0);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (abortRef.current) abortRef.current.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setLoading(true);
    setFlagged([]);
    setScanned(0);

    (async () => {
      const allFlagged: FlaggedListing[] = [];
      let done = 0;

      // Process items in batches of 5
      for (let i = 0; i < SCAN_ITEMS.length; i += 5) {
        if (ac.signal.aborted) break;
        const batch = SCAN_ITEMS.slice(i, i + 5);
        const results = await Promise.all(
          batch.map(item =>
            fetchMarketListings(item, 50, true, ac.signal).catch(() => [] as MarketListing[])
          )
        );

        for (const listings of results) {
          if (listings.length < 3) continue;

          // Compute median price_per_unit for this item
          const prices = listings
            .map(l => l.price_per_unit)
            .filter(p => p > 0)
            .sort((a, b) => a - b);
          if (prices.length === 0) continue;

          const median = prices[Math.floor(prices.length / 2)];

          for (const listing of listings) {
            const ppu = listing.price_per_unit;
            if (ppu <= 0) continue;

            // HIGH: price > 50x median — almost certainly RMT gold transfer
            if (ppu > median * 50) {
              allFlagged.push({
                listing,
                reason: `Listed at ${formatPrice(ppu)}g — ${Math.round(ppu / median)}x the typical price of ~${formatPrice(median)}g. Likely RMT gold transfer.`,
                severity: "high",
              });
            }
            // HIGH: price < median/50 — giving away for free (RMT buyer side or troll)
            else if (ppu < median / 50 && median > 10) {
              allFlagged.push({
                listing,
                reason: `Listed at ${formatPrice(ppu)}g — ${Math.round(median / ppu)}x below the typical price of ~${formatPrice(median)}g. Possible RMT (buyer receives gold via overpriced counter-trade).`,
                severity: "high",
              });
            }
            // MEDIUM: price > 10x median
            else if (ppu > median * 10) {
              allFlagged.push({
                listing,
                reason: `Listed at ${formatPrice(ppu)}g — ${Math.round(ppu / median)}x above the typical ~${formatPrice(median)}g. Suspicious pricing, possible RMT.`,
                severity: "medium",
              });
            }
            // MEDIUM: total price > 50,000g on a cheap item (gold laundering)
            else if (listing.price > 50000 && median < 100) {
              allFlagged.push({
                listing,
                reason: `Total listing price ${formatPrice(listing.price)}g for a ~${formatPrice(median)}g item (qty: ${listing.quantity}). Large gold amount on cheap item — possible gold laundering.`,
                severity: "medium",
              });
            }
          }
        }

        done += batch.length;
        if (!ac.signal.aborted) setScanned(done);
      }

      if (!ac.signal.aborted) {
        // Sort: high severity first, then by price descending
        allFlagged.sort((a, b) => {
          if (a.severity !== b.severity) return a.severity === "high" ? -1 : 1;
          return b.listing.price - a.listing.price;
        });
        setFlagged(allFlagged);
        setLoading(false);
      }
    })();

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
        We scan current marketplace listings for prices that are dramatically above or below
        the typical trade value. These are often RMT (real money trading) gold transfers —
        a player buys a worthless item for 100,000g to transfer gold to another account.
        Seller names are hidden by the API, so we can only show the listing details.
      </p>

      {loading && (
        <div style={{ color: "var(--gold-500)", fontSize: "0.8125rem", padding: "20px 0" }}>
          Scanning {scanned}/{SCAN_ITEMS.length} items...
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
            Found {flagged.length} suspicious listing{flagged.length !== 1 ? "s" : ""} across {SCAN_ITEMS.length} scanned items
          </div>

          <div className={styles.trendTable}>
            <div className={styles.rmtTableHeader}>
              <span></span>
              <span>Item</span>
              <span>Rarity</span>
              <span>Listed Price</span>
              <span>Qty</span>
              <span>Per Unit</span>
              <span>Listed</span>
              <span>Severity</span>
            </div>
            {flagged.map((f, idx) => (
              <div key={idx} className={styles.rmtTableRow}>
                <span>
                  <img
                    src={itemIconPath(f.listing.archetype)}
                    alt="" width={28} height={28}
                    className={styles.itemIcon}
                    onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                  />
                </span>
                <span className={styles.trendItemName}>{f.listing.item}</span>
                <span>
                  <span className={styles[`rarity${f.listing.rarity}`] ?? styles.rarityCommon}>
                    {f.listing.rarity}
                  </span>
                </span>
                <span className={styles.priceCell}>
                  <GoldIcon />{formatPrice(f.listing.price)}
                </span>
                <span style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>
                  {f.listing.quantity}
                </span>
                <span className={styles.priceCell}>
                  <GoldIcon />{formatPrice(f.listing.price_per_unit)}
                </span>
                <span style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>
                  {timeAgo(f.listing.created_at)}
                </span>
                <span className={f.severity === "high" ? styles.rmtHigh : styles.rmtMedium}>
                  {f.severity === "high" ? "HIGH" : "MEDIUM"}
                </span>
              </div>
            ))}
          </div>

          {/* Reasoning panel — show on hover/click would be nice but for now show all */}
          <div style={{ marginTop: 16 }}>
            <div className={styles.sectionHeader}>
              <span className={styles.sectionTitle}>Detection Reasoning</span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {flagged.slice(0, 30).map((f, idx) => (
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
              {flagged.length > 30 && (
                <p style={{ color: "var(--text-muted)", fontSize: "0.6875rem", fontStyle: "italic" }}>
                  ...and {flagged.length - 30} more suspicious listings.
                </p>
              )}
            </div>
          </div>
        </>
      )}

      <div style={{
        fontSize: "0.6875rem", color: "var(--text-muted)",
        fontStyle: "italic", marginTop: 20, opacity: 0.7, lineHeight: 1.7,
      }}>
        <p>
          <strong style={{ color: "var(--gold-500)", fontStyle: "normal" }}>Disclaimer:</strong>{" "}
          This is automated detection based on price anomalies only. Not all flagged listings
          are necessarily RMT — some may be pricing mistakes or intentional gifts. Seller
          identities are not available through the API. This tool is for community awareness only.
        </p>
      </div>
    </div>
  );
}
