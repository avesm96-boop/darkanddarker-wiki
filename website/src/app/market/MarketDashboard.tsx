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

function formatNum(n: number): string {
  if (!n || isNaN(n)) return "—";
  return n.toLocaleString();
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
        (e.target as HTMLImageElement).style.visibility = "hidden";
      }}
    />
  );
}

function PriceCell({ value }: { value: number }) {
  return (
    <span style={{
      textAlign: "right",
      fontVariantNumeric: "tabular-nums",
      display: "flex",
      alignItems: "center",
      justifyContent: "flex-end",
      gap: 3,
    }}>
      {formatGold(value)}<GoldIcon />
    </span>
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

  // High Demand = most sold items (highest trading volume)
  const highDemand = [...trending]
    .filter((t) => t.totalVolume > 0)
    .sort((a, b) => b.totalVolume - a.totalVolume)
    .slice(0, 10);

  return (
    <div className={styles.dashboard}>
      <div>
        <div className={styles.sectionHeader}>
          <span className={styles.sectionTitle}>High Demand Products</span>
        </div>
        {/* 8-column grid: icon | name | avg | lowest | highest | sold | listings | trend */}
        <div className={styles.trendTableHeader}>
          <span></span>
          <span>Item</span>
          <span style={{ textAlign: "right" }}>
            <span title="Average price per unit across active listings">Avg Price</span>
          </span>
          <span style={{ textAlign: "right" }}>
            <span title="Cheapest active listing (price per unit)">Lowest</span>
          </span>
          <span style={{ textAlign: "right" }}>
            <span title="Most expensive active listing (price per unit)">Highest</span>
          </span>
          <span style={{ textAlign: "right" }}>
            <span title="Number of items sold (detected between polling cycles)">Sold</span>
          </span>
          <span style={{ textAlign: "right" }}>
            <span title="Number of active marketplace listings">Active</span>
          </span>
          <span style={{ textAlign: "right" }}>
            <span title="Price trend over recent polls">Trend</span>
          </span>
        </div>
        <div>
          {highDemand.map((t) => (
            <div key={t.archetype} className={styles.trendTableRow}>
              <ItemIcon archetype={t.archetype} />
              <span className={styles.trendItemName}>{t.label}</span>
              <PriceCell value={t.currentAvg} />
              <PriceCell value={t.currentLowest} />
              <PriceCell value={t.avg14d} />
              <span style={{
                textAlign: "right",
                fontWeight: 600,
                color: "var(--gold-500)",
              }}>
                {formatNum(t.totalVolume)}
              </span>
              <span style={{ textAlign: "right", color: "var(--text-muted)" }}>
                {formatNum(t.avg7d)}
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
          High demand items ranked by number of sales detected. Market data is collected
          directly from the in-game marketplace every ~3 minutes across all 741 tradeable items.
        </p>
      </div>
    </div>
  );
}
