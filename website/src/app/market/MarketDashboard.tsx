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
                    dataKey="typical"
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

      <div style={{
        fontSize: "0.6875rem",
        color: "var(--text-muted)",
        fontStyle: "italic",
        marginTop: 20,
        opacity: 0.7,
        lineHeight: 1.7,
        maxWidth: 800,
      }}>
        <p style={{ marginBottom: 8 }}>
          <strong style={{ color: "var(--gold-500)", fontStyle: "normal" }}>How we calculate prices:</strong>{" "}
          Raw market averages are heavily skewed by RMT and troll listings (e.g. 10,000g for a 30g item).
          We use an outlier-resistant method: when a time bucket&apos;s maximum price exceeds 3x the average
          and 10x the minimum, we estimate the typical price as the minimum + 20% instead of using the
          polluted average. This gives a much more accurate picture of what items actually trade for.
        </p>
        <p style={{ marginBottom: 8 }}>
          <strong style={{ color: "var(--gold-500)", fontStyle: "normal" }}>Column definitions:</strong>{" "}
          &quot;Avg 14d/7d/24h&quot; = outlier-adjusted average over that period.
          &quot;Current Avg&quot; = most recent ~8 hours.
          &quot;Lowest Now&quot; = cheapest per-unit listing currently live on the marketplace.
          &quot;Change&quot; = price movement comparing last ~12h vs previous ~24h.
        </p>
        <p>
          Analytics data is aggregated hourly by DarkerDB and may be delayed 3-4 hours.
          Use the <strong style={{ fontStyle: "normal" }}>Search</strong> tab for real-time listing prices.
        </p>
      </div>
    </div>
  );
}
