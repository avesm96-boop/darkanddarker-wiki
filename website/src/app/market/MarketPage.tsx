"use client";

import { useState, useEffect, useCallback } from "react";
import styles from "./market.module.css";
import { fetchPopulation, type PopulationData } from "./api";
import MarketSearchTab from "./MarketSearchTab";

const OUR_API = "/api/market";

function useDataAge() {
  const [lastSeen, setLastSeen] = useState<number | null>(null);
  const [agoText, setAgoText] = useState("—");

  // Fetch last_seen from stats every 10 seconds
  useEffect(() => {
    const fetchAge = () => {
      fetch(`${OUR_API}/stats`)
        .then((r) => r.json())
        .then((d) => {
          const lp = d?.last_poll;
          if (lp?.started_at) setLastSeen(lp.started_at);
        })
        .catch(() => {});
    };
    fetchAge();
    const interval = setInterval(fetchAge, 10_000);
    return () => clearInterval(interval);
  }, []);

  // Tick the "ago" display every second
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
  const [population, setPopulation] = useState<PopulationData | null>(null);
  const dataAge = useDataAge();

  const loadPopulation = useCallback(() => {
    const ac = new AbortController();
    fetchPopulation(ac.signal)
      .then((pop) => { if (!ac.signal.aborted) setPopulation(pop); })
      .catch(() => {});
    return () => ac.abort();
  }, []);

  useEffect(() => {
    const cleanup = loadPopulation();
    const interval = setInterval(loadPopulation, 30_000);
    return () => { cleanup(); clearInterval(interval); };
  }, [loadPopulation]);

  const formatNum = (n: number): string => n.toLocaleString();

  return (
    <div className={styles.page}>
      <div className={`container ${styles.pageInner}`}>
        {/* Header */}
        <div className="section-head" style={{ marginBottom: "36px" }}>
          <span className="section-label">Economy</span>
          <h1 className="section-title">Market</h1>
          <p className="section-desc">
            Live marketplace data — direct from game servers
          </p>
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
              <strong>Live Data</strong> — Prices pulled from in-game marketplace every ~5 seconds
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

        {/* Population Stats */}
        <div className={styles.populationBar}>
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
          {population?.timestamp && (
            <div className={styles.lastUpdated}>
              Last updated: {new Date(population.timestamp).toLocaleTimeString()}
            </div>
          )}
        </div>

        {/* Market Search */}
        <MarketSearchTab />
      </div>
    </div>
  );
}
