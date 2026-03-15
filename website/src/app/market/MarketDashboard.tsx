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
    <div className={styles.trendSection}>
      <div className={styles.sectionHeader}>
        <span className={styles.sectionTitle}>{title}</span>
      </div>
      <div className={styles.trendTable}>
        <div className={styles.trendTableHeader}>
          <span></span>
          <span>Item</span>
          <span>Avg 14d</span>
          <span>Avg 7d</span>
          <span>Avg 24h</span>
          <span>Current Avg</span>
          <span>Lowest Now</span>
          <span>Change</span>
          <span>Chart</span>
        </div>
        {items.map((item) => (
          <div key={item.archetype} className={styles.trendTableRow}>
            <span>
              <ItemIcon archetype={item.archetype} />
            </span>
            <span className={styles.trendItemName}>{item.label}</span>
            <span className={styles.priceCell}>
              <GoldIcon />{formatGold(item.avg14d)}
            </span>
            <span className={styles.priceCell}>
              <GoldIcon />{formatGold(item.avg7d)}
            </span>
            <span className={styles.priceCell}>
              <GoldIcon />{formatGold(item.avg24h)}
            </span>
            <span className={styles.priceCell}>
              <GoldIcon />{formatGold(item.currentAvg)}
            </span>
            <span className={styles.priceCell}>
              {item.currentLowest > 0 ? (
                <><GoldIcon />{formatGold(item.currentLowest)}</>
              ) : (
                <span style={{ color: "var(--text-muted)" }}>&mdash;</span>
              )}
            </span>
            <span className={item.changePct >= 0 ? styles.trendUp : styles.trendDown}>
              {item.changePct >= 0 ? "+" : ""}{item.changePct.toFixed(1)}%
            </span>
            <span className={styles.sparkline}>
              <ResponsiveContainer width={100} height={32}>
                <AreaChart data={item.priceHistory}>
                  <Area
                    type="monotone"
                    dataKey="avg"
                    stroke="rgba(201,168,76,0.6)"
                    fill="rgba(201,168,76,0.1)"
                    strokeWidth={1.5}
                    dot={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
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

  const gainers = trending
    .filter((t) => t.changePct > 0)
    .sort((a, b) => b.changePct - a.changePct)
    .slice(0, 10);
  const losers = trending
    .filter((t) => t.changePct < 0)
    .sort((a, b) => a.changePct - b.changePct)
    .slice(0, 10);
  const mostTraded = [...trending]
    .sort((a, b) => b.totalVolume - a.totalVolume)
    .slice(0, 10);

  return (
    <div className={styles.dashboard}>
      <TrendTable title="Top 10 Gainers" items={gainers} />
      <TrendTable title="Top 10 Losers" items={losers} />
      <TrendTable title="Most Traded" items={mostTraded} />

      <p style={{
        fontSize: "0.6875rem",
        color: "var(--text-muted)",
        fontStyle: "italic",
        marginTop: 16,
        opacity: 0.7,
      }}>
        Analytics data is aggregated hourly and may be delayed 3-4 hours.
        &quot;Current Avg&quot; reflects the most recent aggregated average.
        &quot;Lowest Now&quot; is the cheapest per-unit listing currently on the marketplace.
        Use the Search tab for real-time prices.
      </p>
    </div>
  );
}
