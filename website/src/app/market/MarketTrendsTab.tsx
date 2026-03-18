"use client";

import { useState, useEffect } from "react";
import styles from "./market.module.css";
import {
  fetchMarketTrends,
  fetchMarketDeals,
  fetchMarketFastest,
  fetchMarketVolume,
  fetchMarketSupply,
  fetchMarketSpreads,
  itemIconPath,
  GOLD_ICON,
  type TrendItem,
  type DealItem,
  type FastestItem,
  type VolumeItem,
  type SupplyItem,
  type SpreadItem,
} from "./api";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatGold(n: number): string {
  if (!n || isNaN(n)) return "—";
  return Math.round(n).toLocaleString();
}

function formatTTSell(seconds: number): string {
  if (!seconds || isNaN(seconds)) return "—";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
}

function displayName(raw: string): string {
  return raw.replace(/([A-Z])/g, " $1").trim();
}

// ---------------------------------------------------------------------------
// Shared item cell (icon + name)
// ---------------------------------------------------------------------------

function ItemCell({ marketplaceId, name }: { marketplaceId: string; name: string }) {
  const archetype = marketplaceId.replace("Id.Item.", "");
  return (
    <td className={styles.msItemName}>
      <span className={styles.msItemNameInner}>
        <img
          src={itemIconPath(archetype)}
          alt=""
          width={20}
          height={20}
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = "none";
          }}
        />
        {displayName(name)}
      </span>
    </td>
  );
}

// ---------------------------------------------------------------------------
// Price Movers
// ---------------------------------------------------------------------------

function TrendTable({
  items,
  direction,
}: {
  items: TrendItem[];
  direction: "rising" | "falling";
}) {
  if (items.length === 0) {
    return <div className={styles.msEmpty}>No {direction} items found.</div>;
  }
  return (
    <div className={styles.msTableWrap}>
      <table className={styles.msTable}>
        <thead>
          <tr>
            <th style={{ width: 30 }}>#</th>
            <th>Item</th>
            <th style={{ width: 90 }}>Now</th>
            <th style={{ width: 90 }}>Was</th>
            <th style={{ width: 80 }}>Change</th>
            <th style={{ width: 60 }}>Listed</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, idx) => (
            <tr key={item.item_marketplace_id}>
              <td style={{ color: "var(--text-muted)", fontSize: "0.7rem" }}>{idx + 1}</td>
              <ItemCell marketplaceId={item.item_marketplace_id} name={item.name} />
              <td className={styles.msPrice}>
                <span className={styles.msPriceInner}>
                  {formatGold(item.current_min)}
                  <img src={GOLD_ICON} alt="" width={12} height={12} />
                </span>
              </td>
              <td
                style={{
                  color: "var(--text-muted)",
                  fontSize: "0.72rem",
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {formatGold(item.previous_min)}
              </td>
              <td
                style={{
                  fontWeight: 600,
                  fontSize: "0.75rem",
                  fontVariantNumeric: "tabular-nums",
                  color:
                    direction === "rising"
                      ? "rgba(201,120,76,0.9)"
                      : "rgba(76,201,100,0.9)",
                }}
              >
                {direction === "rising" ? "+" : ""}
                {item.change_pct}%
              </td>
              <td className={styles.msTime}>{item.active_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Best Deals
// ---------------------------------------------------------------------------

const RARITY_CLASS: Record<string, keyof typeof styles> = {
  Poor: "rarityPoor",
  Common: "rarityCommon",
  Uncommon: "rarityUncommon",
  Rare: "rarityRare",
  Epic: "rarityEpic",
  Legendary: "rarityLegendary",
  Unique: "rarityUnique",
  Artifact: "rarityArtifact",
};

function DealsTable({ items }: { items: DealItem[] }) {
  if (items.length === 0) {
    return <div className={styles.msEmpty}>No deals found.</div>;
  }
  return (
    <div className={styles.msTableWrap}>
      <table className={styles.msTable}>
        <thead>
          <tr>
            <th style={{ width: 30 }}>#</th>
            <th>Item</th>
            <th style={{ width: 100 }}>Price</th>
            <th style={{ width: 100 }}>Fair Value</th>
            <th style={{ width: 80 }}>Discount</th>
            <th style={{ width: 90 }}>Rarity</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, idx) => {
            const rarityKey = RARITY_CLASS[item.base_rarity] ?? "rarityCommon";
            return (
              <tr key={item.listing_id}>
                <td style={{ color: "var(--text-muted)", fontSize: "0.7rem" }}>{idx + 1}</td>
                <ItemCell
                  marketplaceId={item.item_marketplace_id}
                  name={item.item_base_name}
                />
                <td className={styles.msPrice}>
                  <span className={styles.msPriceInner}>
                    {formatGold(item.price)}
                    <img src={GOLD_ICON} alt="" width={12} height={12} />
                  </span>
                </td>
                <td
                  style={{
                    color: "var(--text-muted)",
                    fontSize: "0.72rem",
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  {formatGold(item.fair_value)}
                </td>
                <td
                  style={{
                    fontWeight: 600,
                    fontSize: "0.75rem",
                    fontVariantNumeric: "tabular-nums",
                    color: "rgba(76,201,100,0.9)",
                  }}
                >
                  -{item.discount_pct}%
                </td>
                <td>
                  <span className={`${styles.rarityBadge} ${styles[rarityKey]}`}>
                    {item.base_rarity}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Fastest Selling
// ---------------------------------------------------------------------------

function FastestTable({ items }: { items: FastestItem[] }) {
  if (items.length === 0) {
    return <div className={styles.msEmpty}>No data found.</div>;
  }
  return (
    <div className={styles.msTableWrap}>
      <table className={styles.msTable}>
        <thead>
          <tr>
            <th style={{ width: 30 }}>#</th>
            <th>Item</th>
            <th style={{ width: 90 }}>Avg Time</th>
            <th style={{ width: 60 }}>Sold</th>
            <th style={{ width: 100 }}>Avg Price</th>
            <th style={{ width: 60 }}>Active</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, idx) => (
            <tr key={item.item_marketplace_id}>
              <td style={{ color: "var(--text-muted)", fontSize: "0.7rem" }}>{idx + 1}</td>
              <ItemCell
                marketplaceId={item.item_marketplace_id}
                name={item.item_base_name}
              />
              <td
                style={{
                  fontWeight: 600,
                  fontSize: "0.75rem",
                  fontVariantNumeric: "tabular-nums",
                  color: "var(--gold-400)",
                }}
              >
                {formatTTSell(item.avg_time_to_sell)}
              </td>
              <td className={styles.msTime}>{item.sold_count}</td>
              <td className={styles.msPrice}>
                <span className={styles.msPriceInner}>
                  {formatGold(item.avg_price)}
                  <img src={GOLD_ICON} alt="" width={12} height={12} />
                </span>
              </td>
              <td className={styles.msTime}>{item.active_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Most Traded (Volume)
// ---------------------------------------------------------------------------

function VolumeTable({ items }: { items: VolumeItem[] }) {
  if (items.length === 0) {
    return <div className={styles.msEmpty}>No data found.</div>;
  }
  return (
    <div className={styles.msTableWrap}>
      <table className={styles.msTable}>
        <thead>
          <tr>
            <th style={{ width: 30 }}>#</th>
            <th>Item</th>
            <th style={{ width: 60 }}>Sales</th>
            <th style={{ width: 100 }}>Avg Price</th>
            <th style={{ width: 120 }}>Total Gold</th>
            <th style={{ width: 60 }}>Active</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, idx) => (
            <tr key={item.item_marketplace_id}>
              <td style={{ color: "var(--text-muted)", fontSize: "0.7rem" }}>{idx + 1}</td>
              <ItemCell
                marketplaceId={item.item_marketplace_id}
                name={item.item_base_name}
              />
              <td
                style={{
                  fontWeight: 600,
                  fontSize: "0.75rem",
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {item.sold_count}
              </td>
              <td className={styles.msPrice}>
                <span className={styles.msPriceInner}>
                  {formatGold(item.avg_price)}
                  <img src={GOLD_ICON} alt="" width={12} height={12} />
                </span>
              </td>
              <td className={styles.msPrice}>
                <span className={styles.msPriceInner}>
                  {formatGold(item.total_gold)}
                  <img src={GOLD_ICON} alt="" width={12} height={12} />
                </span>
              </td>
              <td className={styles.msTime}>{item.active_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Supply Watch
// ---------------------------------------------------------------------------

function SupplyTable({
  items,
  direction,
}: {
  items: SupplyItem[];
  direction: "draining" | "flooding";
}) {
  if (items.length === 0) {
    return (
      <div className={styles.msEmpty}>No {direction} supply items found.</div>
    );
  }
  return (
    <div className={styles.msTableWrap}>
      <table className={styles.msTable}>
        <thead>
          <tr>
            <th style={{ width: 30 }}>#</th>
            <th>Item</th>
            <th style={{ width: 70 }}>Now</th>
            <th style={{ width: 70 }}>Was</th>
            <th style={{ width: 70 }}>Change</th>
            <th style={{ width: 100 }}>Min Price</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, idx) => (
            <tr key={item.item_marketplace_id}>
              <td style={{ color: "var(--text-muted)", fontSize: "0.7rem" }}>{idx + 1}</td>
              <td className={styles.msItemName}>
                <span className={styles.msItemNameInner}>
                  {displayName(item.name)}
                </span>
              </td>
              <td
                style={{
                  fontVariantNumeric: "tabular-nums",
                  fontSize: "0.75rem",
                }}
              >
                {item.current_count}
              </td>
              <td
                style={{
                  color: "var(--text-muted)",
                  fontSize: "0.72rem",
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {item.previous_count}
              </td>
              <td
                style={{
                  fontWeight: 600,
                  fontSize: "0.75rem",
                  fontVariantNumeric: "tabular-nums",
                  color:
                    direction === "draining"
                      ? "rgba(76,201,100,0.9)"
                      : "rgba(201,120,76,0.9)",
                }}
              >
                {item.change > 0 ? "+" : ""}
                {item.change}
              </td>
              <td className={styles.msPrice}>
                <span className={styles.msPriceInner}>
                  {formatGold(item.min_price)}
                  <img src={GOLD_ICON} alt="" width={12} height={12} />
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Price Spreads
// ---------------------------------------------------------------------------

function SpreadsTable({ items }: { items: SpreadItem[] }) {
  if (items.length === 0) {
    return <div className={styles.msEmpty}>No spread data found.</div>;
  }
  return (
    <div className={styles.msTableWrap}>
      <table className={styles.msTable}>
        <thead>
          <tr>
            <th style={{ width: 30 }}>#</th>
            <th>Item</th>
            <th style={{ width: 90 }}>Lowest</th>
            <th style={{ width: 90 }}>Median</th>
            <th style={{ width: 90 }}>Spread</th>
            <th style={{ width: 80 }}>Spread%</th>
            <th style={{ width: 60 }}>Active</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, idx) => (
            <tr key={item.item_marketplace_id}>
              <td style={{ color: "var(--text-muted)", fontSize: "0.7rem" }}>{idx + 1}</td>
              <td className={styles.msItemName}>
                <span className={styles.msItemNameInner}>
                  {displayName(item.name)}
                </span>
              </td>
              <td className={styles.msPrice}>
                <span className={styles.msPriceInner}>
                  {formatGold(item.min_price)}
                  <img src={GOLD_ICON} alt="" width={12} height={12} />
                </span>
              </td>
              <td
                style={{
                  color: "var(--text-muted)",
                  fontSize: "0.72rem",
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {formatGold(item.median_price)}
              </td>
              <td className={styles.msPrice}>
                <span className={styles.msPriceInner}>
                  {formatGold(item.spread)}
                  <img src={GOLD_ICON} alt="" width={12} height={12} />
                </span>
              </td>
              <td
                style={{
                  fontWeight: 600,
                  fontSize: "0.75rem",
                  fontVariantNumeric: "tabular-nums",
                  color: "rgba(201,168,76,0.9)",
                }}
              >
                {item.spread_pct}%
              </td>
              <td className={styles.msTime}>{item.active_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface TrendsState {
  rising: TrendItem[];
  falling: TrendItem[];
  deals: DealItem[];
  fastest: FastestItem[];
  volume: VolumeItem[];
  supplyDraining: SupplyItem[];
  supplyFlooding: SupplyItem[];
  spreads: SpreadItem[];
}

const EMPTY_STATE: TrendsState = {
  rising: [],
  falling: [],
  deals: [],
  fastest: [],
  volume: [],
  supplyDraining: [],
  supplyFlooding: [],
  spreads: [],
};

export default function MarketTrendsTab() {
  const [data, setData] = useState<TrendsState>(EMPTY_STATE);
  const [loading, setLoading] = useState(true);
  const [hours, setHours] = useState<24 | 48 | 168>(24);
  const [category, setCategory] = useState<"" | "equipment" | "misc">("");

  useEffect(() => {
    const ac = new AbortController();
    setLoading(true);

    Promise.all([
      fetchMarketTrends(hours, ac.signal, category),
      fetchMarketDeals(category, ac.signal),
      fetchMarketFastest(category, hours, ac.signal),
      fetchMarketVolume(category, hours, ac.signal),
      fetchMarketSupply(category, hours, ac.signal),
      fetchMarketSpreads(category, ac.signal),
    ])
      .then(([trends, deals, fastest, volume, supply, spreads]) => {
        if (ac.signal.aborted) return;
        setData({
          rising: trends.rising,
          falling: trends.falling,
          deals,
          fastest,
          volume,
          supplyDraining: supply.draining,
          supplyFlooding: supply.flooding,
          spreads,
        });
        setLoading(false);
      })
      .catch(() => {
        if (!ac.signal.aborted) setLoading(false);
      });

    return () => ac.abort();
  }, [hours, category]);

  return (
    <div className={styles.dashboard}>
      {/* Controls bar */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 20,
          gap: 12,
          flexWrap: "wrap",
        }}
      >
        {/* Category toggle — left */}
        <div className={styles.msChartToggle}>
          {(
            [
              { value: "", label: "All" },
              { value: "equipment", label: "Equipment" },
              { value: "misc", label: "Misc" },
            ] as const
          ).map(({ value, label }) => (
            <button
              key={value}
              className={
                category === value ? styles.msChartBtnActive : styles.msChartBtn
              }
              onClick={() => setCategory(value)}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Timeframe toggle — right */}
        <div className={styles.msChartToggle}>
          {([24, 48, 168] as const).map((h) => (
            <button
              key={h}
              className={hours === h ? styles.msChartBtnActive : styles.msChartBtn}
              onClick={() => setHours(h)}
            >
              {h === 24 ? "24H" : h === 48 ? "48H" : "7D"}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className={styles.msEmpty}>Loading trends...</div>
      ) : (
        <>
          {/* ── 1. Price Movers ── */}
          <div
            style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 32 }}
          >
            <div className={styles.msSection}>
              <div className={styles.sectionHeader}>
                <span
                  className={styles.sectionTitle}
                  style={{ display: "flex", alignItems: "center", gap: 8 }}
                >
                  <span style={{ color: "rgba(76,201,100,0.9)" }}>&#9660;</span>
                  Price Drops
                </span>
              </div>
              <TrendTable items={data.falling} direction="falling" />
            </div>

            <div className={styles.msSection}>
              <div className={styles.sectionHeader}>
                <span
                  className={styles.sectionTitle}
                  style={{ display: "flex", alignItems: "center", gap: 8 }}
                >
                  <span style={{ color: "rgba(201,120,76,0.9)" }}>&#9650;</span>
                  Price Rises
                </span>
              </div>
              <TrendTable items={data.rising} direction="rising" />
            </div>
          </div>

          {/* ── 2. Best Deals ── */}
          <div className={styles.msSection} style={{ marginBottom: 32 }}>
            <div className={styles.sectionHeader}>
              <span className={styles.sectionTitle}>
                Best Deals — Below Fair Value
              </span>
            </div>
            <DealsTable items={data.deals} />
          </div>

          {/* ── 3. Fastest Selling ── */}
          <div className={styles.msSection} style={{ marginBottom: 32 }}>
            <div className={styles.sectionHeader}>
              <span className={styles.sectionTitle}>Fastest Selling</span>
            </div>
            <FastestTable items={data.fastest} />
          </div>

          {/* ── 4. Most Traded ── */}
          <div className={styles.msSection} style={{ marginBottom: 32 }}>
            <div className={styles.sectionHeader}>
              <span className={styles.sectionTitle}>Most Traded</span>
            </div>
            <VolumeTable items={data.volume} />
          </div>

          {/* ── 5. Supply Watch ── */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 32 }}>
            <div className={styles.msSection}>
              <div className={styles.sectionHeader}>
                <span
                  className={styles.sectionTitle}
                  style={{ display: "flex", alignItems: "center", gap: 8 }}
                >
                  <span style={{ color: "rgba(76,201,100,0.9)" }}>&#9660;</span>
                  Supply Draining
                </span>
              </div>
              <SupplyTable items={data.supplyDraining} direction="draining" />
            </div>

            <div className={styles.msSection}>
              <div className={styles.sectionHeader}>
                <span
                  className={styles.sectionTitle}
                  style={{ display: "flex", alignItems: "center", gap: 8 }}
                >
                  <span style={{ color: "rgba(201,120,76,0.9)" }}>&#9650;</span>
                  Supply Flooding
                </span>
              </div>
              <SupplyTable items={data.supplyFlooding} direction="flooding" />
            </div>
          </div>

          {/* ── 6. Price Spreads ── */}
          <div className={styles.msSection}>
            <div className={styles.sectionHeader}>
              <span className={styles.sectionTitle}>
                Flip Opportunities — Price Spreads
              </span>
            </div>
            <SpreadsTable items={data.spreads} />
          </div>
        </>
      )}
    </div>
  );
}
