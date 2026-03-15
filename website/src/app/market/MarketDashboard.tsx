"use client";

import styles from "./market.module.css";
import type { PopulationData, TrendingItem } from "./api";

interface Props {
  population: PopulationData | null;
  trending: TrendingItem[];
  loading: boolean;
}

function formatNum(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return n.toLocaleString();
}

function formatGold(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return Math.round(n).toLocaleString();
}

export default function MarketDashboard({ population, trending, loading }: Props) {
  // Skeleton loading state
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
          <span className={styles.sectionTitle}>Trending</span>
        </div>
        <div className={styles.trendingGrid}>
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className={styles.skeletonCard} style={{ height: 52 }} />
          ))}
        </div>
      </div>
    );
  }

  const gainers = trending.filter((t) => t.changePct > 0).slice(0, 5);
  const losers = trending.filter((t) => t.changePct < 0).slice(0, 5);
  const mostTraded = [...trending]
    .sort((a, b) => b.recentVolume - a.recentVolume)
    .slice(0, 5);

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

      {/* Trending: Gainers */}
      {gainers.length > 0 && (
        <>
          <div className={styles.sectionHeader}>
            <span className={styles.sectionTitle}>Top Gainers</span>
          </div>
          <div className={styles.trendingGrid}>
            {gainers.map((item) => (
              <div key={item.archetype} className={styles.trendItem}>
                <span className={styles.trendItemName}>{item.label}</span>
                <span className={styles.trendItemPrice}>{formatGold(item.currentAvg)}g</span>
                <span className={`${styles.trendItemChange} ${styles.trendUp}`}>
                  +{item.changePct.toFixed(1)}%
                </span>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Trending: Losers */}
      {losers.length > 0 && (
        <>
          <div className={styles.sectionHeader}>
            <span className={styles.sectionTitle}>Top Losers</span>
          </div>
          <div className={styles.trendingGrid}>
            {losers.map((item) => (
              <div key={item.archetype} className={styles.trendItem}>
                <span className={styles.trendItemName}>{item.label}</span>
                <span className={styles.trendItemPrice}>{formatGold(item.currentAvg)}g</span>
                <span className={`${styles.trendItemChange} ${styles.trendDown}`}>
                  {item.changePct.toFixed(1)}%
                </span>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Most Traded */}
      {mostTraded.length > 0 && (
        <>
          <div className={styles.sectionHeader}>
            <span className={styles.sectionTitle}>Most Traded</span>
          </div>
          <div className={styles.trendingGrid}>
            {mostTraded.map((item) => (
              <div key={item.archetype} className={styles.trendItem}>
                <span className={styles.trendItemName}>{item.label}</span>
                <span className={styles.trendItemPrice}>{formatGold(item.currentAvg)}g</span>
                <span className={styles.trendItemChange} style={{ color: "var(--text-muted)" }}>
                  Vol: {formatNum(item.recentVolume)}
                </span>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Last Updated */}
      {population?.timestamp && (
        <div className={styles.lastUpdated}>
          Last updated: {new Date(population.timestamp).toLocaleTimeString()}
        </div>
      )}
    </div>
  );
}
