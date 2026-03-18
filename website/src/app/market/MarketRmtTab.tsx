"use client";

import { useState, useEffect } from "react";
import styles from "./market.module.css";
import {
  fetchRmtStats,
  fetchRmtSellers,
  itemIconPath,
  GOLD_ICON,
  type RmtStats,
  type RmtSeller,
} from "./api";

function formatGold(n: number): string {
  if (!n || isNaN(n)) return "—";
  return Math.round(n).toLocaleString();
}

export default function MarketRmtTab() {
  const [stats, setStats] = useState<RmtStats | null>(null);
  const [sellers, setSellers] = useState<RmtSeller[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const ctrl = new AbortController();
    const { signal } = ctrl;

    setLoading(true);

    Promise.all([fetchRmtStats(signal), fetchRmtSellers(10, signal)])
      .then(([s, sv]) => {
        setStats(s);
        setSellers(sv);
        setLoading(false);
      })
      .catch((err) => {
        if (err.name !== "AbortError") setLoading(false);
      });

    return () => ctrl.abort();
  }, []);

  if (loading) {
    return (
      <div className={styles.msEmpty} style={{ paddingTop: 48 }}>
        Loading RMT data...
      </div>
    );
  }

  return (
    <div className={styles.dashboard}>
      {/* ── Section 1: Overview Stats ── */}
      <div className={styles.msSection}>
        <div className={styles.sectionHeader}>
          <span className={styles.sectionTitle}>Detection Overview</span>
        </div>

        <div className={styles.msPriceCards}>
          {/* Flagged Listings */}
          <div className={styles.msPriceCard}>
            <div
              className={styles.msPriceCardValue}
              style={{ color: "rgba(220, 80, 80, 0.9)" }}
            >
              {stats?.hard_flagged?.toLocaleString() ?? "—"}
            </div>
            <div className={styles.msPriceCardLabel}>Flagged Listings</div>
          </div>

          {/* Estimated RMT Gold */}
          <div className={styles.msPriceCard}>
            <div className={styles.msPriceCardValue}>
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 4,
                }}
              >
                {formatGold(stats?.estimated_rmt_gold ?? 0)}
                <img src={GOLD_ICON} alt="" width={14} height={14} />
              </span>
            </div>
            <div className={styles.msPriceCardLabel}>Est. RMT Gold</div>
          </div>

          {/* Flagged Sellers */}
          <div className={styles.msPriceCard}>
            <div
              className={styles.msPriceCardValue}
              style={{ color: "rgba(220, 80, 80, 0.9)" }}
            >
              {stats?.flagged_sellers?.toLocaleString() ?? "—"}
            </div>
            <div className={styles.msPriceCardLabel}>Flagged Sellers</div>
          </div>

          {/* Detection Models */}
          <div className={styles.msPriceCard}>
            <div className={styles.msPriceCardValue}>
              {stats?.models_count?.toLocaleString() ?? "—"}
            </div>
            <div className={styles.msPriceCardLabel}>Detection Models</div>
          </div>
        </div>
      </div>

      {/* ── Section 2: Top Suspected RMT Sellers ── */}
      <div className={styles.msSection}>
        <div className={styles.sectionHeader}>
          <span className={styles.sectionTitle}>
            Top Suspected RMT Sellers
          </span>
        </div>

        {sellers.length === 0 ? (
          <div className={styles.msEmpty}>No seller data available.</div>
        ) : (
          <div className={styles.msTableWrap}>
            <table className={styles.msTable}>
              <thead>
                <tr>
                  <th style={{ width: 30 }}>#</th>
                  <th>Seller</th>
                  <th style={{ width: 70 }}>Active</th>
                  <th style={{ width: 70 }}>Total</th>
                  <th style={{ width: 70 }}>Flagged</th>
                  <th style={{ width: 90 }}>Flag Rate</th>
                  <th style={{ width: 110 }}>Avg Price Ratio</th>
                </tr>
              </thead>
              <tbody>
                {sellers.map((seller, idx) => (
                  <tr key={seller.seller_info}>
                    <td
                      style={{
                        color: "var(--text-muted)",
                        fontSize: "0.7rem",
                      }}
                    >
                      {idx + 1}
                    </td>
                    <td
                      className={styles.msItemName}
                      style={{ fontVariantNumeric: "tabular-nums" }}
                    >
                      {seller.seller_info}
                    </td>
                    <td className={styles.msTime}>{seller.active_listings}</td>
                    <td className={styles.msTime}>{seller.total_listings}</td>
                    <td className={styles.msTime}>
                      {seller.flagged_hard + seller.flagged_soft}
                    </td>
                    <td
                      style={{
                        fontWeight: 600,
                        fontSize: "0.75rem",
                        fontVariantNumeric: "tabular-nums",
                        color: "rgba(220, 80, 80, 0.9)",
                      }}
                    >
                      {Math.round(seller.flag_rate * 100)}%
                    </td>
                    <td
                      style={{
                        fontWeight: 600,
                        fontSize: "0.75rem",
                        fontVariantNumeric: "tabular-nums",
                        color: "rgba(201, 120, 76, 0.9)",
                      }}
                    >
                      {seller.avg_price_ratio
                        ? `${Math.round(seller.avg_price_ratio)}×`
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Section 3: Top RMT Items ── */}
      <div className={styles.msSection}>
        <div className={styles.sectionHeader}>
          <span className={styles.sectionTitle}>Top RMT Items</span>
        </div>

        {!stats?.top_rmt_items?.length ? (
          <div className={styles.msEmpty}>No item data available.</div>
        ) : (
          <div className={styles.msTableWrap}>
            <table className={styles.msTable}>
              <thead>
                <tr>
                  <th style={{ width: 30 }}>#</th>
                  <th>Item</th>
                  <th style={{ width: 130 }}>Flagged Listings</th>
                  <th style={{ width: 130 }}>Total RMT Gold</th>
                </tr>
              </thead>
              <tbody>
                {stats.top_rmt_items.map((item, idx) => {
                  const displayName = item.item_base_name
                    .replace(/([A-Z])/g, " $1")
                    .trim();
                  return (
                    <tr key={item.item_marketplace_id}>
                      <td
                        style={{
                          color: "var(--text-muted)",
                          fontSize: "0.7rem",
                        }}
                      >
                        {idx + 1}
                      </td>
                      <td className={styles.msItemName}>
                        <span className={styles.msItemNameInner}>
                          <img
                            src={itemIconPath(item.item_base_name)}
                            alt=""
                            width={20}
                            height={20}
                            onError={(e) => {
                              (
                                e.target as HTMLImageElement
                              ).style.display = "none";
                            }}
                          />
                          {displayName}
                        </span>
                      </td>
                      <td
                        style={{
                          color: "rgba(220, 80, 80, 0.9)",
                          fontWeight: 600,
                          fontVariantNumeric: "tabular-nums",
                          fontSize: "0.75rem",
                        }}
                      >
                        {item.flagged_count.toLocaleString()}
                      </td>
                      <td className={styles.msPrice}>
                        <span className={styles.msPriceInner}>
                          {formatGold(item.total_rmt_gold)}
                          <img src={GOLD_ICON} alt="" width={12} height={12} />
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
