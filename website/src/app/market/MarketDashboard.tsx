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
          <span title="What this item typically sold for over the past week. We ignore unrealistic prices (like 1g or 99,999g troll/RMT listings) to show what real players actually pay.">Avg 7d</span>
          <span title="What this item typically sold for in the last 24 hours, with fake prices filtered out.">Avg 24h</span>
          <span title="The most recent typical price based on the last few hours of trade data. Note: market data updates every few hours, so this may be slightly behind real-time.">Current Avg</span>
          <span title="A realistic low-end price from current marketplace listings. DarkerDB data has a lag, so the absolute cheapest listings have often already sold. We use the 25th percentile to show what you'd realistically find available right now.">Low Range</span>
          <span title="How much the price moved recently — compares the last ~12 hours to the previous ~24 hours. A positive number means the price went up.">Change</span>
          <span title="Visual price trend over the past week. The line shows typical trade prices with fake listings filtered out.">Trend</span>
        </div>
        {items.map((item) => (
          <div key={item.archetype} className={styles.trendTableRow}>
            <span>
              <ItemIcon archetype={item.archetype} />
            </span>
            <span className={styles.trendItemName}>{item.label}</span>
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
          <strong style={{ color: "var(--gold-500)", fontStyle: "normal" }}>How we handle fake prices:</strong>{" "}
          The marketplace has many troll listings (items at 1g) and RMT listings (items at 99,999g)
          that ruin the average. We automatically strip the most extreme prices from each time window
          to get closer to what the item actually trades for. However, some items (especially currency
          items like Silver Coin) have so many fake listings that even cleaned averages may be off.
          For those items, the <strong style={{ fontStyle: "normal" }}>&quot;Low Range&quot;</strong> column
          is the most reliable — it shows the real cheapest price on the market right now, with
          troll prices filtered out.
        </p>
        <p style={{ marginBottom: 8 }}>
          <strong style={{ color: "var(--gold-500)", fontStyle: "normal" }}>What to trust most:</strong>{" "}
          &quot;Low Range&quot; is always real-time and outlier-filtered from 50 live listings.
          The averages (7d, 24h, Current) are best for items with clean trading patterns
          (like Wolf Pelt, Bone Powder). For RMT-heavy items, focus on &quot;Low Range&quot; instead.
        </p>
        <p>
          Market data is provided by DarkerDB and updates every few hours.
          Hover over column headers for details. Use the <strong style={{ fontStyle: "normal" }}>Search</strong> tab
          for real-time listing prices.
        </p>
      </div>
    </div>
  );
}
