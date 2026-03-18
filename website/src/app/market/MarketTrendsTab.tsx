"use client";

import { useState, useEffect } from "react";
import styles from "./market.module.css";
import { fetchMarketTrends, itemIconPath, GOLD_ICON, type TrendItem } from "./api";

function formatGold(n: number): string {
  if (!n || isNaN(n)) return "—";
  return Math.round(n).toLocaleString();
}

function TrendTable({ items, direction }: { items: TrendItem[]; direction: "rising" | "falling" }) {
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
          {items.map((item, idx) => {
            const archetype = item.item_marketplace_id.replace("Id.Item.", "");
            const displayName = item.name.replace(/([A-Z])/g, " $1").trim();
            return (
              <tr key={item.item_marketplace_id}>
                <td style={{ color: "var(--text-muted)", fontSize: "0.7rem" }}>{idx + 1}</td>
                <td className={styles.msItemName}>
                  <span className={styles.msItemNameInner}>
                    <img
                      src={itemIconPath(archetype)}
                      alt="" width={20} height={20}
                      onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                    />
                    {displayName}
                  </span>
                </td>
                <td className={styles.msPrice}>
                  <span className={styles.msPriceInner}>
                    {formatGold(item.current_min)}
                    <img src={GOLD_ICON} alt="" width={12} height={12} />
                  </span>
                </td>
                <td style={{ color: "var(--text-muted)", fontSize: "0.72rem", fontVariantNumeric: "tabular-nums" }}>
                  {formatGold(item.previous_min)}
                </td>
                <td style={{
                  fontWeight: 600,
                  fontSize: "0.75rem",
                  fontVariantNumeric: "tabular-nums",
                  color: direction === "rising"
                    ? "rgba(201,120,76,0.9)"
                    : "rgba(76,201,100,0.9)",
                }}>
                  {direction === "rising" ? "+" : ""}{item.change_pct}%
                </td>
                <td className={styles.msTime}>{item.active_count}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function MarketTrendsTab() {
  const [rising, setRising] = useState<TrendItem[]>([]);
  const [falling, setFalling] = useState<TrendItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [hours, setHours] = useState<24 | 48 | 168>(24);

  useEffect(() => {
    const ac = new AbortController();
    setLoading(true);
    fetchMarketTrends(hours, ac.signal)
      .then((data) => {
        if (!ac.signal.aborted) {
          setRising(data.rising);
          setFalling(data.falling);
          setLoading(false);
        }
      })
      .catch(() => { if (!ac.signal.aborted) setLoading(false); });
    return () => ac.abort();
  }, [hours]);

  return (
    <div className={styles.dashboard}>
      {/* Timeframe toggle */}
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 20 }}>
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
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
          {/* Falling prices */}
          <div className={styles.msSection}>
            <div className={styles.sectionHeader}>
              <span className={styles.sectionTitle} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ color: "rgba(76,201,100,0.9)" }}>&#9660;</span>
                Price Drops
              </span>
            </div>
            <TrendTable items={falling} direction="falling" />
          </div>

          {/* Rising prices */}
          <div className={styles.msSection}>
            <div className={styles.sectionHeader}>
              <span className={styles.sectionTitle} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ color: "rgba(201,120,76,0.9)" }}>&#9650;</span>
                Price Rises
              </span>
            </div>
            <TrendTable items={rising} direction="rising" />
          </div>
        </div>
      )}
    </div>
  );
}
