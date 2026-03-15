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

        {/* Dashboard */}
        <MarketDashboard
          population={population}
          trending={trending}
          loading={loading}
        />

        <div className={styles.sectionDivider} />

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
      </div>
    </div>
  );
}
