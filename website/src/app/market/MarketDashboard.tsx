"use client";

import styles from "./market.module.css";
import type { TrendingItem } from "./api";
import { itemIconPath, GOLD_ICON } from "./api";
import { ResponsiveContainer, AreaChart, Area } from "recharts";

interface Props {
  trending: TrendingItem[];
  loading: boolean;
}

function formatGold(n: number): string {
  if (!n || isNaN(n)) return "—";
  return Math.round(n).toLocaleString();
}

function GoldIcon() {
  return (
    <img
      src={GOLD_ICON}
      alt=""
      width={14}
      height={14}
      style={{ verticalAlign: "middle", marginRight: 2 }}
    />
  );
}

function ItemIcon({ archetype }: { archetype: string }) {
  return (
    <img
      src={itemIconPath(archetype)}
      alt=""
      width={32}
      height={32}
      className={styles.itemIcon}
      onError={(e) => {
        (e.target as HTMLImageElement).style.display = "none";
      }}
    />
  );
}

function TrendTable({
  title,
  items,
}: {
  title: string;
  items: TrendingItem[];
}) {
  if (items.length === 0) return null;

  return (
    <div>
      <div className={styles.sectionHeader}>
        <span className={styles.sectionTitle}>{title}</span>
      </div>
      {/* 8-column grid matching CSS: icon | name | col3 | col4 | col5 | col6 | col7 | sparkline */}
      <div className={styles.trendTableHeader}>
        <span></span>
        <span>Item</span>
        <span style={{ textAlign: "right" }}>
          <span title="Average price per unit across all active listings">Avg Price</span>
        </span>
        <span style={{ textAlign: "right" }}>
          <span title="Cheapest active listing right now (per unit)">Lowest</span>
        </span>
        <span style={{ textAlign: "right" }}>
          <span title="Most expensive active listing (per unit)">Highest</span>
        </span>
        <span style={{ textAlign: "right" }}>
          <span title="Number of active marketplace listings">Listings</span>
        </span>
        <span style={{ textAlign: "right" }}>
          <span title="Number of items sold (disappeared between polls)">Sold</span>
        </span>
        <span style={{ textAlign: "right" }}>
          <span title="Price trend over recent polls">Trend</span>
        </span>
      </div>
      <div>
        {items.map((t) => (
          <div key={t.archetype} className={styles.trendTableRow}>
            <ItemIcon archetype={t.archetype} />
            <span className={styles.trendItemName}>{t.label}</span>
            <span style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 3 }}>
              {formatGold(t.currentAvg)}<GoldIcon />
            </span>
            <span style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 3 }}>
              {formatGold(t.currentLowest)}<GoldIcon />
            </span>
            <span style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 3, color: "var(--text-muted)" }}>
              {formatGold(t.avg14d)}<GoldIcon />
            </span>
            <span style={{ textAlign: "right", color: "var(--text-muted)" }}>
              {t.avg7d}
            </span>
            <span style={{ textAlign: "right", color: t.totalVolume > 0 ? "var(--gold-500)" : "var(--text-muted)" }}>
              {t.totalVolume}
            </span>
            <span>
              {t.priceHistory.length > 1 ? (
                <ResponsiveContainer width="100%" height={28}>
                  <AreaChart
                    data={t.priceHistory.map((p) => ({
                      t: p.timestamp,
                      v: p.avg || p.min || 0,
                    }))}
                  >
                    <Area
                      type="monotone"
                      dataKey="v"
                      stroke="rgba(201,168,76,0.6)"
                      fill="rgba(201,168,76,0.1)"
                      strokeWidth={1.5}
                      dot={false}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <span style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>
                  building...
                </span>
              )}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function MarketDashboard({ trending, loading }: Props) {
  if (loading) {
    return (
      <div className={styles.dashboard}>
        <div className={styles.sectionHeader}>
          <span className={styles.sectionTitle}>Loading market data...</span>
        </div>
        <div className={styles.trendingGrid}>
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className={styles.skeletonCard} style={{ height: 52 }} />
          ))}
        </div>
      </div>
    );
  }

  // Show three views of the data
  const mostListed = [...trending]
    .filter((t) => t.avg7d > 0)
    .sort((a, b) => b.avg7d - a.avg7d)
    .slice(0, 10);

  const mostSold = [...trending]
    .filter((t) => t.totalVolume > 0)
    .sort((a, b) => b.totalVolume - a.totalVolume)
    .slice(0, 10);

  const mostValuable = [...trending]
    .filter((t) => t.currentAvg > 0)
    .sort((a, b) => b.currentAvg - a.currentAvg)
    .slice(0, 10);

  return (
    <div className={styles.dashboard}>
      <TrendTable title="Most Listed" items={mostListed} />
      <TrendTable title="Most Sold" items={mostSold} />
      <TrendTable title="Most Valuable" items={mostValuable} />

      <div style={{
        fontSize: "0.6875rem",
        color: "var(--text-muted)",
        fontStyle: "italic",
        marginTop: 20,
        opacity: 0.7,
        lineHeight: 1.7,
        maxWidth: 800,
      }}>
        <p>
          Market data is collected directly from the in-game marketplace every ~60 seconds.
          All 741 tradeable items are scanned each cycle. Prices shown are per unit.
          Trend sparklines will become more detailed as historical data accumulates.
        </p>
      </div>
    </div>
  );
}
