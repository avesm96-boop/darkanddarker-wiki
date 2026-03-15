"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import Image from "next/image";
import styles from "./quests.module.css";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Reward {
  type: "item" | "exp" | "affinity" | "random";
  id?: string;
  name?: string;
  count: number;
  merchant?: string;
}

interface Objective {
  type: string;
  count?: number;
  target?: string;
  dungeons?: string[];
  item_type?: string;
  rarity?: string;
  single_session?: boolean;
  [key: string]: unknown;
}

interface Quest {
  id: string;
  required_level?: number;
  required_quest?: string;
  rewards: Reward[];
  objectives?: Objective[];
  chapter_id?: string;
  chapter_name?: string;
  chapter_order?: number;
  title?: string;
  title_localized?: string;
}

interface Merchant {
  id: string;
  name: string;
  portrait: string;
  quest_count: number;
  quests: Quest[];
}

interface QuestsData {
  generated_at: string;
  stats: {
    total_merchants: number;
    total_quests: number;
  };
  merchants: Merchant[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Convert "Id_Item_GoldCoins" -> "GoldCoins" for icon path */
function itemIdToIconName(id: string): string {
  return id.replace(/^Id_Item_/, "");
}

/** Human-friendly quest ID: "Id_Quest_Alchemist_01" -> "Alchemist #01" */
function formatQuestId(id: string): string {
  const m = id.match(/^Id_Quest_(\w+?)_(\d+)$/);
  if (m) return `${m[1].replace(/_/g, " ")} #${m[2]}`;
  return id.replace(/^Id_Quest_/, "").replace(/_/g, " ");
}

/** Format a required_quest reference into a readable name */
function formatPrereq(id: string): string {
  return formatQuestId(id);
}

/** Objective type -> CSS class */
function objectiveClass(type: string): string {
  switch (type) {
    case "kill":
    case "damage":
      return styles.objectiveKill;
    case "fetch":
    case "hold":
    case "useitem":
      return styles.objectiveFetch;
    case "explore":
    case "escape":
      return styles.objectiveExplore;
    default:
      return styles.objectiveGeneric;
  }
}

/** Build a human-readable description of an objective */
function describeObjective(obj: Objective): string {
  const parts: string[] = [];
  switch (obj.type) {
    case "kill":
      parts.push(`Kill ${obj.count ?? "?"} ${obj.target ?? "enemies"}`);
      break;
    case "fetch":
      if (obj.item_type) {
        parts.push(`Collect ${obj.count ?? "?"} ${obj.rarity ? obj.rarity + " " : ""}${obj.item_type} items`);
      } else if (obj.target) {
        parts.push(`Collect ${obj.count ?? "?"} ${obj.target}`);
      } else {
        parts.push(`Fetch ${obj.count ?? "?"} items`);
      }
      break;
    case "explore":
      parts.push(`Explore ${obj.target ?? "area"}`);
      if (obj.count && obj.count > 1) parts[0] += ` (x${obj.count})`;
      break;
    case "escape":
      parts.push(`Escape ${obj.count ?? 1} time${(obj.count ?? 1) > 1 ? "s" : ""}`);
      break;
    case "damage":
      parts.push(`Deal ${obj.count ?? "?"} damage to ${obj.target ?? "enemies"}`);
      break;
    case "hold":
      parts.push(`Hold ${obj.count ?? "?"} ${obj.target ?? "items"}`);
      break;
    case "useitem":
      parts.push(`Use ${obj.count ?? "?"} ${obj.target ?? "items"}`);
      break;
    case "props":
      parts.push(`Interact with ${obj.count ?? "?"} ${obj.target ?? "props"}`);
      break;
    default:
      parts.push(`${obj.type}: ${obj.count ?? "?"}`);
  }
  if (obj.single_session) parts.push("(single run)");
  return parts.join(" ");
}

// ---------------------------------------------------------------------------
// Sub-Components
// ---------------------------------------------------------------------------

function RewardChip({ reward }: { reward: Reward }) {
  if (reward.type === "exp") {
    return (
      <span className={styles.rewardChip}>
        <span className={styles.rewardXp}>{reward.count} XP</span>
      </span>
    );
  }

  if (reward.type === "affinity") {
    return (
      <span className={styles.rewardChip}>
        <span className={styles.rewardAffinity}>
          {reward.count} Affinity
          {reward.merchant ? ` (${reward.merchant})` : ""}
        </span>
      </span>
    );
  }

  if (reward.type === "random") {
    const label = reward.id
      ? reward.id
          .replace(/^Id_RandomReward_Quest_/, "")
          .replace(/_/g, " ")
      : "Random Reward";
    return (
      <span className={styles.rewardChip}>
        <span className={styles.rewardCount}>{reward.count}x</span>
        <span className={styles.rewardRandom}>{label}</span>
      </span>
    );
  }

  // item reward
  const iconName = reward.id ? itemIdToIconName(reward.id) : "";
  const iconPath = iconName ? `/item-icons/Item_Icon_${iconName}.png` : "";

  return (
    <span className={styles.rewardChip}>
      {iconPath && (
        <RewardIcon src={iconPath} alt={reward.name ?? "item"} />
      )}
      <span className={styles.rewardCount}>{reward.count}</span>
      <span className={styles.rewardName}>{reward.name ?? "Item"}</span>
    </span>
  );
}

function RewardIcon({ src, alt }: { src: string; alt: string }) {
  const [show, setShow] = useState(true);
  if (!show) return null;
  return (
    <img
      src={src}
      alt={alt}
      className={styles.rewardIcon}
      onError={() => setShow(false)}
    />
  );
}

function MerchantPortrait({
  src,
  name,
  size,
  className,
  fallbackClass,
}: {
  src: string;
  name: string;
  size: number;
  className: string;
  fallbackClass: string;
}) {
  const [failed, setFailed] = useState(false);

  if (failed) {
    return (
      <div className={fallbackClass}>
        {name.charAt(0).toUpperCase()}
      </div>
    );
  }

  return (
    <img
      src={src}
      alt={name}
      className={className}
      width={size}
      height={size}
      onError={() => setFailed(true)}
    />
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function QuestsPage() {
  const [data, setData] = useState<QuestsData | null>(null);
  const [error, setError] = useState(false);
  const [selectedMerchant, setSelectedMerchant] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const loadData = useCallback(() => {
    setError(false);
    setData(null);
    fetch("/data/quests.json")
      .then((r) => {
        if (!r.ok) throw new Error("fetch failed");
        return r.json();
      })
      .then((json: QuestsData) => setData(json))
      .catch(() => setError(true));
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Sort merchants alphabetically
  const merchants = useMemo(() => {
    if (!data) return [];
    return [...data.merchants].sort((a, b) => a.name.localeCompare(b.name));
  }, [data]);

  // Filtered merchants for grid view
  const filteredMerchants = useMemo(() => {
    if (!search.trim()) return merchants;
    const q = search.toLowerCase();
    return merchants.filter((m) => m.name.toLowerCase().includes(q));
  }, [merchants, search]);

  // Currently selected merchant
  const merchant = useMemo(() => {
    if (!selectedMerchant) return null;
    return merchants.find((m) => m.id === selectedMerchant) ?? null;
  }, [merchants, selectedMerchant]);

  // Group quests by chapter, sorted by chapter_order
  const questChapters = useMemo(() => {
    if (!merchant) return [];
    const sorted = [...merchant.quests].sort(
      (a, b) => (a.chapter_order ?? 0) - (b.chapter_order ?? 0)
    );
    const chapters: { name: string; order: number; quests: Quest[] }[] = [];
    const chapterMap = new Map<string, { name: string; order: number; quests: Quest[] }>();

    for (const q of sorted) {
      const key = q.chapter_id ?? q.chapter_name ?? "Uncategorized";
      let ch = chapterMap.get(key);
      if (!ch) {
        ch = { name: q.chapter_name ?? "Uncategorized", order: q.chapter_order ?? 0, quests: [] };
        chapterMap.set(key, ch);
        chapters.push(ch);
      }
      ch.quests.push(q);
    }

    return chapters;
  }, [merchant]);

  // Build a lookup for quest IDs -> names within this merchant for prereq display
  const questNameLookup = useMemo(() => {
    if (!data) return new Map<string, string>();
    const map = new Map<string, string>();
    for (const m of data.merchants) {
      for (const q of m.quests) {
        map.set(q.id, formatQuestId(q.id));
      }
    }
    return map;
  }, [data]);

  // -- Loading state --
  if (!data && !error) {
    return (
      <div className={styles.page}>
        <div className={styles.pageInner}>
          <div className="section-head" style={{ marginBottom: 36 }}>
            <span className="section-label">Objectives</span>
            <h1 className="section-title">Quest Tracker</h1>
          </div>
          <div className={styles.skeletonGrid}>
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className={styles.skeletonCard}>
                <div className={styles.skeletonCircle} />
                <div className={styles.skeletonBarWide} />
                <div className={styles.skeletonBarNarrow} />
                <div className={styles.skeletonBarBtn} />
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // -- Error state --
  if (error) {
    return (
      <div className={styles.page}>
        <div className={styles.pageInner}>
          <div className="section-head">
            <span className="section-label">Objectives</span>
            <h1 className="section-title">Quest Tracker</h1>
          </div>
          <div className={styles.errorState}>
            <p className={styles.errorText}>Failed to load quest data</p>
            <button className={styles.retryButton} onClick={loadData}>
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  // -- Merchant Detail View --
  if (merchant) {
    return (
      <div className={styles.page}>
        <div className={styles.pageInner}>
          <button
            className={styles.backButton}
            onClick={() => setSelectedMerchant(null)}
          >
            <span className={styles.backArrow}>&larr;</span>
            All Merchants
          </button>

          <div className={styles.detailHeader}>
            <MerchantPortrait
              src={merchant.portrait}
              name={merchant.name}
              size={96}
              className={styles.detailPortrait}
              fallbackClass={styles.detailPortraitFallback}
            />
            <div className={styles.detailInfo}>
              <h1 className={styles.detailName}>{merchant.name}</h1>
              <span className={styles.detailSub}>
                {merchant.quests.length} quest{merchant.quests.length !== 1 ? "s" : ""}
              </span>
            </div>
          </div>

          {questChapters.map((chapter) => (
            <div key={chapter.name + chapter.order} className={styles.chapterGroup}>
              <h2 className={styles.chapterTitle}>{chapter.name}</h2>
              <div className={styles.timeline}>
                {chapter.quests.map((quest) => (
                  <div key={quest.id} className={styles.questNode}>
                    <div className={styles.questDot} />
                    <div className={styles.questNodeHeader}>
                      <span className={styles.questId}>
                        {quest.title_localized ?? formatQuestId(quest.id)}
                      </span>
                      {quest.required_level != null && (
                        <span className={styles.questLevel}>
                          Level {quest.required_level}
                        </span>
                      )}
                    </div>

                    <div className={styles.questMeta}>
                      {quest.required_quest && (
                        <div className={styles.questMetaRow}>
                          <span className={styles.metaLabel}>Prerequisite</span>
                          <span className={styles.prereqLink}>
                            {questNameLookup.get(quest.required_quest) ??
                              formatPrereq(quest.required_quest)}
                          </span>
                        </div>
                      )}

                      {quest.objectives && quest.objectives.length > 0 && (
                        <div className={styles.questMetaRow} style={{ alignItems: "flex-start" }}>
                          <span className={styles.metaLabel}>Objectives</span>
                          <div className={styles.objectivesList}>
                            {quest.objectives.map((obj, idx) => (
                              <div key={idx} className={styles.objectiveItem}>
                                <span className={objectiveClass(obj.type)}>
                                  {obj.type}
                                </span>
                                <span>{describeObjective(obj)}</span>
                                {obj.dungeons && obj.dungeons.length > 0 && (
                                  <span className={styles.objectiveDungeon}>
                                    in {obj.dungeons.join(", ")}
                                  </span>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>

                    {quest.rewards && quest.rewards.length > 0 && (
                      <div className={styles.rewardsRow}>
                        <span className={styles.rewardsLabel}>Rewards</span>
                        {quest.rewards.map((reward, idx) => (
                          <RewardChip key={idx} reward={reward} />
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}

          {questChapters.length === 0 && (
            <div className={styles.emptyState}>
              No quests found for this merchant.
            </div>
          )}
        </div>
      </div>
    );
  }

  // -- Merchant Grid View (default) --
  return (
    <div className={styles.page}>
      <div className={styles.pageInner}>
        <div className="section-head" style={{ marginBottom: 36 }}>
          <span className="section-label">Objectives</span>
          <h1 className="section-title">Quest Tracker</h1>
          <p className="section-desc">
            {data!.stats.total_quests} quests across {data!.stats.total_merchants} merchants.
            Select a merchant to browse their quest chain.
          </p>
          <div className={styles.headerDivider} />
        </div>

        <div className={styles.searchBar}>
          <input
            type="text"
            placeholder="Search merchants..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className={styles.searchInput}
          />
        </div>

        {filteredMerchants.length === 0 ? (
          <div className={styles.emptyState}>No merchants match your search</div>
        ) : (
          <div className={styles.merchantGrid}>
            {filteredMerchants.map((m) => (
              <div
                key={m.id}
                className={styles.merchantCard}
                onClick={() => setSelectedMerchant(m.id)}
              >
                <MerchantPortrait
                  src={m.portrait}
                  name={m.name}
                  size={128}
                  className={styles.merchantPortrait}
                  fallbackClass={styles.merchantPortraitFallback}
                />
                <div className={styles.merchantName}>{m.name}</div>
                <div className={styles.merchantQuestCount}>
                  {m.quest_count} quest{m.quest_count !== 1 ? "s" : ""}
                </div>
                <div className={styles.viewQuestsBtn}>View Quests &rarr;</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
