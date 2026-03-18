"use client";

import { useState, useEffect } from "react";
import styles from "./market.module.css";
import MarketSearchTab from "./MarketSearchTab";

const OUR_API = "/api/market";

function useDataAge() {
  const [lastSeen, setLastSeen] = useState<number | null>(null);
  const [agoText, setAgoText] = useState("—");

  useEffect(() => {
    const fetchAge = () => {
      fetch(`${OUR_API}/stats?_t=${Date.now()}`, { cache: "no-store" })
        .then((r) => r.json())
        .then((d) => { if (d?.last_data_at) setLastSeen(d.last_data_at); })
        .catch(() => {});
    };
    fetchAge();
    const interval = setInterval(fetchAge, 10_000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!lastSeen) return;
    const tick = () => {
      const sec = Math.floor(Date.now() / 1000 - lastSeen);
      if (sec < 60) setAgoText(`${sec}s ago`);
      else if (sec < 3600) setAgoText(`${Math.floor(sec / 60)}m ${sec % 60}s ago`);
      else setAgoText(`${Math.floor(sec / 3600)}h ago`);
    };
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [lastSeen]);

  return agoText;
}

export default function MarketPage() {
  const dataAge = useDataAge();

  return (
    <div className={styles.page}>
      <div className={`container ${styles.pageInner}`}>
        {/* Header */}
        <div className="section-head" style={{ marginBottom: "36px" }}>
          <span className="section-label">Economy</span>
          <h1 className="section-title">Market</h1>
        </div>

        {/* Live data banner */}
        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 10,
          padding: "12px 20px",
          marginBottom: 24,
          background: "rgba(76, 201, 100, 0.06)",
          border: "1px solid rgba(76, 201, 100, 0.2)",
          borderRadius: 8,
          fontSize: "0.75rem",
          color: "var(--gold-500)",
          lineHeight: 1.6,
          flexWrap: "wrap",
        }}>
          <span style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{
              width: 8, height: 8, flexShrink: 0,
              background: "#4cc964",
              borderRadius: "50%",
              animation: "pulse-glow 2s ease-in-out infinite",
            }} />
            <span>
              <strong>Live</strong> — Prices update approximately every ~10 seconds
            </span>
          </span>
          <span style={{
            fontSize: "0.7rem",
            color: "rgba(76, 201, 100, 0.8)",
            fontVariantNumeric: "tabular-nums",
            whiteSpace: "nowrap",
          }}>
            Last scan: {dataAge}
          </span>
        </div>

        {/* Market Search */}
        <MarketSearchTab />
      </div>
    </div>
  );
}
