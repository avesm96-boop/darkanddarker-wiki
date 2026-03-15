"use client";

import styles from "./market.module.css";
import type { PopulationData, TrendingItem, TrendingRange } from "./api";

interface Props {
  population: PopulationData | null;
  trending: TrendingItem[];
  loading: boolean;
  range: TrendingRange;
  onRangeChange: (range: TrendingRange) => void;
}

function formatNum(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return n.toLocaleString();
}

function formatGold(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return Math.round(n).toLocaleString();
}

function TrendTable({
  title,
  items,
  showChange,
}: {
  title: string;
  items: TrendingItem[];
  showChange?: boolean;
}) {
  if (items.length === 0) return null;

  return (
    <>
      <div className={styles.sectionHeader}>
        <span className={styles.sectionTitle}>{title}</span>
      </div>
      <div className={styles.trendTable}>
        <div className={styles.trendTableHeader}>
          <span>Item</span>
          <span>Avg Was</span>
          <span>Avg Now</span>
          {showChange && <span>Change</span>}
          <span>Volume</span>
        </div>
        {items.map((item) => (
          <div key={item.archetype} className={styles.trendTableRow}>
            <span className={styles.trendItemName}>{item.label}</span>
            <span className={styles.trendItemPrice}>{formatGold(item.previousAvg)}g</span>
            <span className={styles.trendItemPrice}>{formatGold(item.currentAvg)}g</span>
            {showChange && (
              <span className={item.changePct >= 0 ? styles.trendUp : styles.trendDown}>
                {item.changePct >= 0 ? "+" : ""}{item.changePct.toFixed(1)}%
              </span>
            )}
            <span style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>
              {formatNum(item.recentVolume)}
            </span>
          </div>
        ))}
      </div>
    </>
  );
}

export default function MarketDashboard({ population, trending, loading, range, onRangeChange }: Props) {
  if (loading) {
    return (
      <div className={styles.dashboard}>
        <div className={styles.sectionHeader}>
          <span className={styles.sectionTitle}>Server Population</span>
        </div>
        <div className={styles.dashboardGrid}>
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className={styles.skeletonCard} />
          ))}
        </div>
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
    .slice(0, 5);
  const losers = trending
    .filter((t) => t.changePct < 0)
    .sort((a, b) => a.changePct - b.changePct)
    .slice(0, 5);
  const mostTraded = [...trending]
    .sort((a, b) => b.recentVolume - a.recentVolume)
    .slice(0, 5);

  const rangeLabel = range === "24h" ? "Last 24 Hours" : "Last 7 Days";

  return (
    <div className={styles.dashboard}>
      {/* Population Stats */}
      <div className={styles.sectionHeader}>
        <span className={styles.sectionTitle}>Server Population</span>
      </div>
      <div className={styles.dashboardGrid}>
        <div className={styles.statCard}>
          <div className={styles.statValue}>
            {population ? formatNum(population.num_online) : "\u2014"}
          </div>
          <div className={styles.statLabel}>Online</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statValue}>
            {population ? formatNum(population.num_lobby) : "\u2014"}
          </div>
          <div className={styles.statLabel}>In Lobby</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statValue}>
            {population ? formatNum(population.num_dungeon) : "\u2014"}
          </div>
          <div className={styles.statLabel}>In Dungeon</div>
        </div>
      </div>

      {/* Range Selector */}
      <div className={styles.sectionHeader} style={{ marginTop: 24 }}>
        <span className={styles.sectionTitle}>Market Trends — {rangeLabel}</span>
        <div className={styles.timeRangeBar}>
          <button
            className={range === "24h" ? styles.timeRangeBtnActive : styles.timeRangeBtn}
            onClick={() => onRangeChange("24h")}
          >
            24h
          </button>
          <button
            className={range === "7d" ? styles.timeRangeBtnActive : styles.timeRangeBtn}
            onClick={() => onRangeChange("7d")}
          >
            7d
          </button>
        </div>
      </div>

      <TrendTable title="Top Gainers" items={gainers} showChange />
      <TrendTable title="Top Losers" items={losers} showChange />
      <TrendTable title="Most Traded" items={mostTraded} />

      {/* Last Updated */}
      {population?.timestamp && (
        <div className={styles.lastUpdated}>
          Last updated: {new Date(population.timestamp).toLocaleTimeString()}
        </div>
      )}
    </div>
  );
}
