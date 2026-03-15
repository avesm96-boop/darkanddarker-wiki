"use client";

import { useState, useEffect, useRef } from "react";
import styles from "./market.module.css";
import { fetchPriceHistory, type PricePoint } from "./api";
import {
  ComposedChart,
  Area,
  Line,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const GOLD_ICON = "/item-icons/Item_Icon_GoldCoin.png";

interface Props {
  itemId: string;
  itemName: string;
}

type TimeRange = "24h" | "7d" | "30d";

const INTERVAL_MAP: Record<TimeRange, string> = {
  "24h": "1h",
  "7d": "4h",
  "30d": "1d",
};

const RANGE_LABELS: TimeRange[] = ["24h", "7d", "30d"];

interface ChartPoint {
  time: string;
  avg: number;
  min: number;
  max: number;
  volume: number;
  range: [number, number];
}

function formatGold(n: number): string {
  return Math.round(n).toLocaleString();
}

function formatGoldAxis(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return Math.round(n).toLocaleString();
}

function formatTime(ts: string, range: TimeRange): string {
  const d = new Date(ts);
  if (range === "24h") {
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
  if (range === "7d") {
    return d.toLocaleDateString([], { month: "short", day: "numeric", hour: "2-digit" });
  }
  return d.toLocaleDateString([], { month: "short", day: "numeric" });
}

function GoldCoin({ size = 14 }: { size?: number }) {
  return (
    <img
      src={GOLD_ICON}
      alt="gold"
      width={size}
      height={size}
      style={{ verticalAlign: "middle", marginRight: 2 }}
    />
  );
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload || payload.length === 0) return null;
  const data = payload[0]?.payload as ChartPoint | undefined;
  if (!data) return null;

  return (
    <div
      style={{
        background: "rgba(20, 18, 14, 0.95)",
        border: "1px solid rgba(201, 168, 76, 0.2)",
        borderRadius: 8,
        padding: "10px 14px",
        fontSize: "0.75rem",
        lineHeight: 1.6,
        color: "#e8e0d0",
      }}
    >
      <div style={{ color: "rgba(201, 168, 76, 0.7)", marginBottom: 4 }}>{data.time}</div>
      <div style={{ fontVariantNumeric: "tabular-nums" }}>Avg: <strong style={{ color: "#c9a84c" }}><GoldCoin />{formatGold(data.avg)}</strong></div>
      <div style={{ fontVariantNumeric: "tabular-nums" }}>Min: <GoldCoin />{formatGold(data.min)}</div>
      <div style={{ fontVariantNumeric: "tabular-nums" }}>Max: <GoldCoin />{formatGold(data.max)}</div>
      <div style={{ fontVariantNumeric: "tabular-nums" }}>Volume: {data.volume.toLocaleString()}</div>
    </div>
  );
}

export default function MarketItemDetail({ itemId, itemName }: Props) {
  const [range, setRange] = useState<TimeRange>("7d");
  const [data, setData] = useState<ChartPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (abortRef.current) abortRef.current.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setLoading(true);

    // Use archetype from itemId — strip trailing _XXXX id suffix if present
    const archetype = itemId.replace(/_\d+$/, "");

    fetchPriceHistory(archetype, INTERVAL_MAP[range], ac.signal)
      .then((points) => {
        if (!ac.signal.aborted) {
          const chartData: ChartPoint[] = points.map((p) => ({
            time: formatTime(p.timestamp, range),
            avg: p.avg,
            min: p.min,
            max: p.max,
            volume: p.volume,
            range: [p.min, p.max] as [number, number],
          }));
          setData(chartData);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!ac.signal.aborted) {
          setData([]);
          setLoading(false);
        }
      });

    return () => ac.abort();
  }, [itemId, range]);

  // Compute summary stats
  const stats = data.length > 0
    ? {
        avgPrice: data.reduce((s, d) => s + d.avg, 0) / data.length,
        minPrice: Math.min(...data.map((d) => d.min)),
        maxPrice: Math.max(...data.map((d) => d.max)),
        totalVolume: data.reduce((s, d) => s + d.volume, 0),
      }
    : null;

  return (
    <>
      {/* Time Range Buttons */}
      <div className={styles.timeRangeBar}>
        {RANGE_LABELS.map((r) => (
          <button
            key={r}
            className={r === range ? styles.timeRangeBtnActive : styles.timeRangeBtn}
            onClick={() => setRange(r)}
          >
            {r}
          </button>
        ))}
      </div>

      {/* Chart */}
      {loading ? (
        <div className={styles.skeletonChart} />
      ) : data.length === 0 ? (
        <div className={styles.listingsEmpty}>
          No price data available for this time range.
        </div>
      ) : (
        <div className={styles.chartContainer}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 10, right: 10, bottom: 0, left: 0 }}>
              <XAxis
                dataKey="time"
                tick={{ fill: "#7a7060", fontSize: 10 }}
                tickLine={false}
                axisLine={{ stroke: "rgba(201,168,76,0.1)" }}
              />
              <YAxis
                yAxisId="price"
                tick={{ fill: "#7a7060", fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: number) => formatGoldAxis(v)}
              />
              <YAxis
                yAxisId="volume"
                orientation="right"
                tick={{ fill: "#4a4540", fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: number) => formatGoldAxis(v)}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area
                yAxisId="price"
                type="monotone"
                dataKey="range"
                fill="rgba(201,168,76,0.08)"
                stroke="none"
              />
              <Line
                yAxisId="price"
                type="monotone"
                dataKey="avg"
                stroke="#c9a84c"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: "#c9a84c" }}
              />
              <Bar
                yAxisId="volume"
                dataKey="volume"
                fill="rgba(201,168,76,0.15)"
                radius={[2, 2, 0, 0]}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Stats Summary */}
      {stats && (
        <div className={styles.statsGrid}>
          <div className={styles.statsGridCard}>
            <div className={styles.statsGridValue} style={{ fontVariantNumeric: "tabular-nums" }}><GoldCoin size={16} />{formatGold(stats.avgPrice)}</div>
            <div className={styles.statsGridLabel}>Avg Price</div>
          </div>
          <div className={styles.statsGridCard}>
            <div className={styles.statsGridValue} style={{ fontVariantNumeric: "tabular-nums" }}><GoldCoin size={16} />{formatGold(stats.minPrice)}</div>
            <div className={styles.statsGridLabel}>Min</div>
          </div>
          <div className={styles.statsGridCard}>
            <div className={styles.statsGridValue} style={{ fontVariantNumeric: "tabular-nums" }}><GoldCoin size={16} />{formatGold(stats.maxPrice)}</div>
            <div className={styles.statsGridLabel}>Max</div>
          </div>
          <div className={styles.statsGridCard}>
            <div className={styles.statsGridValue} style={{ fontVariantNumeric: "tabular-nums" }}>{stats.totalVolume.toLocaleString()}</div>
            <div className={styles.statsGridLabel}>24h Volume</div>
          </div>
        </div>
      )}
    </>
  );
}
