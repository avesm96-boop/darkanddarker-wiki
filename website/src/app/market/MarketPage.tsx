"use client";

import { useState, useEffect, useCallback } from "react";
import styles from "./market.module.css";
import {
  fetchPopulation,
  fetchTrending,
  type PopulationData,
  type TrendingItem,
} from "./api";
import MarketDashboard from "./MarketDashboard";
import MarketSearch from "./MarketSearch";
import MarketItemDetail from "./MarketItemDetail";
import MarketListings from "./MarketListings";

interface SelectedItem {
  id: string;
  name: string;
}

export default function MarketPage() {
  const [population, setPopulation] = useState<PopulationData | null>(null);
  const [trending, setTrending] = useState<TrendingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedItem, setSelectedItem] = useState<SelectedItem | null>(null);
  const [activeTab, setActiveTab] = useState<"trends" | "search">("trends");

  const loadData = useCallback(() => {
    const ac = new AbortController();
    setLoading(true);
    setError(null);

    Promise.all([
      fetchPopulation(ac.signal).catch(() => null),
      fetchTrending(ac.signal).catch(() => []),
    ])
      .then(([pop, trend]) => {
        if (!ac.signal.aborted) {
          setPopulation(pop);
          setTrending(trend as TrendingItem[]);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!ac.signal.aborted) {
          setError("Failed to load market data. The API may be temporarily unavailable.");
          setLoading(false);
        }
      });

    return () => ac.abort();
  }, []);

  useEffect(() => {
    const cleanup = loadData();
    return cleanup;
  }, [loadData]);

  const handleSelect = useCallback((item: { id: string; name: string }) => {
    setSelectedItem(item);
  }, []);

  const handleClear = useCallback(() => {
    setSelectedItem(null);
  }, []);

  const formatNum = (n: number): string => n.toLocaleString();

  return (
    <div className={styles.page}>
      <div className={`container ${styles.pageInner}`}>
        {/* Header */}
        <div className="section-head" style={{ marginBottom: "36px" }}>
          <span className="section-label">Economy</span>
          <h1 className="section-title">Market</h1>
          <p className="section-desc">
            Live marketplace data powered by DarkerDB
          </p>
        </div>

        {/* Error Banner */}
        {error && (
          <div className={styles.errorBanner}>
            <span>{error}</span>
            <button className={styles.retryBtn} onClick={loadData}>
              Retry
            </button>
          </div>
        )}

        {/* Population Stats — always visible above tabs */}
        <div className={styles.populationBar}>
          <div className={styles.sectionHeader}>
            <span className={styles.sectionTitle}>Server Population</span>
          </div>
          <div className={styles.dashboardGrid}>
            {loading ? (
              Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className={styles.skeletonCard} />
              ))
            ) : (
              <>
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
              </>
            )}
          </div>
          {population?.timestamp && (
            <div className={styles.lastUpdated}>
              Last updated: {new Date(population.timestamp).toLocaleTimeString()}
            </div>
          )}
        </div>

        {/* Tab Bar */}
        <div className={styles.tabBar}>
          <button
            className={activeTab === "trends" ? styles.tabBtnActive : styles.tabBtn}
            onClick={() => setActiveTab("trends")}
          >
            Trends
          </button>
          <button
            className={activeTab === "search" ? styles.tabBtnActive : styles.tabBtn}
            onClick={() => setActiveTab("search")}
          >
            Search
          </button>
        </div>

        {/* Tab Content */}
        {activeTab === "trends" && (
          <MarketDashboard
            trending={trending}
            loading={loading}
          />
        )}

        {activeTab === "search" && (
          <>
            {/* Search */}
            <MarketSearch onSelect={handleSelect} />

            {/* Item Detail */}
            {selectedItem && (
              <>
                <div className={styles.itemDetail}>
                  <div className={styles.itemHeader}>
                    <div>
                      <h2 className={styles.itemName}>{selectedItem.name}</h2>
                      <p className={styles.itemSubtitle}>Price history and statistics</p>
                    </div>
                    <button className={styles.retryBtn} onClick={handleClear}>
                      Close
                    </button>
                  </div>
                  <MarketItemDetail
                    itemId={selectedItem.id}
                    itemName={selectedItem.name}
                  />
                </div>

                <MarketListings itemName={selectedItem.name} />
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
