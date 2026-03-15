"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import styles from "./quests.module.css";

// ---------------------------------------------------------------------------
// Types (matching new quests.json schema — chapters-based)
// ---------------------------------------------------------------------------

interface Objective {
  content_type: string;
  count?: number;
  target?: string;
  target_tag?: string;
  item?: string;
  item_name?: string;
  item_type?: string;
  rarity?: string;
  loot_state?: string;
  dungeons?: string[];
  module?: string;
  description?: string;
  single_session?: boolean;
  kill_type?: string;
  hold_time?: number;
  props_type?: string;
}

interface Reward {
  type: string; // "Item" | "Exp" | "Affinity" | "Random" | etc.
  count?: number;
  id?: string;
  name?: string;
  rarity?: string;
  item_type?: string;
  merchant?: string;
}

interface Prerequisite {
  id: string;
  title: string;
}

interface Quest {
  id: string;
  title: string;
  quest_number: number;
  required_level: number;
  greeting: string;
  completion_text: string;
  prerequisite: Prerequisite | null;
  dungeons: string[];
  objectives: Objective[];
  rewards: Reward[];
}

interface Chapter {
  name: string;
  order: number;
  quests: Quest[];
}

interface Merchant {
  id: string;
  name: string;
  portrait: string;
  chapters: Chapter[];
}

interface QuestsData {
  generated_at: string;
  source: string;
  total_quests: number;
  total_merchants: number;
  merchants: Merchant[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const RARITY_COLORS: Record<string, string> = {
  Poor: "#888",
  Common: "#aaa",
  Uncommon: "#55c075",
  Rare: "#5588dd",
  Epic: "#aa55cc",
  Legendary: "#c9a84c",
  Unique: "#cc4444",
};

function formatId(id: string): string {
  return id
    .replace(/_\d+$/, "")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/_/g, " ");
}

/** Strip "Id_Item_" prefix and trailing "_XXXX" numbers, return icon path */
function itemIconUrl(itemId: string): string {
  const stripped = itemId.replace(/^Id_Item_/, "").replace(/_\d+$/, "");
  return `/item-icons/Item_Icon_${stripped}.png`;
}

/** Get total quest count across all chapters */
function getMerchantQuestCount(merchant: Merchant): number {
  return merchant.chapters.reduce((acc, ch) => acc + ch.quests.length, 0);
}

// ---------------------------------------------------------------------------
// Sub-Components
// ---------------------------------------------------------------------------

function SafeIcon({
  src,
  alt,
  className,
}: {
  src: string;
  alt: string;
  className?: string;
}) {
  const [show, setShow] = useState(true);
  if (!show) return null;
  return (
    <img
      src={src}
      alt={alt}
      className={className}
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

function ObjectiveRow({ obj }: { obj: Objective }) {
  const type = obj.content_type;
  const badgeClass =
    type === "Kill" || type === "Damage"
      ? styles.objBadgeKill
      : type === "Fetch" || type === "Hold" || type === "UseItem"
      ? styles.objBadgeFetch
      : type === "Explore" || type === "Escape"
      ? styles.objBadgeExplore
      : styles.objBadgeGeneric;

  let label = obj.description || type;
  let detail = "";
  let icon: string | null = null;
  let rarityColor: string | undefined;

  switch (type) {
    case "Kill":
      label = obj.target ? `Kill ${obj.target}` : "Kill enemies";
      detail = `Count: ${obj.count ?? "?"}`;
      break;
    case "Fetch":
      label = obj.item_name ? `Fetch ${obj.item_name}` : "Fetch items";
      if (obj.item) icon = itemIconUrl(obj.item);
      if (obj.rarity) {
        label += ` (${obj.rarity})`;
        rarityColor = RARITY_COLORS[obj.rarity];
      }
      detail = `Count: ${obj.count ?? "?"}`;
      if (obj.loot_state) detail += ` | Condition: ${obj.loot_state}`;
      break;
    case "Explore":
      label = obj.module ? `Explore ${obj.module}` : "Explore area";
      if (obj.count && obj.count > 1) detail = `Count: ${obj.count}`;
      break;
    case "Escape":
      label = `Escape ${obj.count ?? 1} time${(obj.count ?? 1) > 1 ? "s" : ""}`;
      break;
    case "Damage":
      label = obj.kill_type
        ? `Deal damage to ${obj.kill_type}`
        : "Deal damage";
      detail = `Amount: ${obj.count ?? "?"}`;
      break;
    case "Hold":
      label = obj.module ? `Hold ${obj.module}` : "Hold position";
      detail = obj.hold_time ? `Duration: ${obj.hold_time}s` : `Count: ${obj.count ?? "?"}`;
      break;
    case "UseItem":
      label = obj.item_name
        ? `Use ${obj.item_name}`
        : "Use items";
      if (obj.item) icon = itemIconUrl(obj.item);
      detail = `Count: ${obj.count ?? "?"}`;
      break;
    case "Props":
      label = obj.target
        ? `${obj.props_type || "Interact"} ${obj.target}`
        : "Interact with props";
      detail = `Count: ${obj.count ?? "?"}`;
      break;
    default:
      label = obj.description || `${type}`;
      if (obj.count) detail = `Count: ${obj.count}`;
  }

  // Add dungeon info to detail
  if (obj.dungeons && obj.dungeons.length > 0) {
    detail += (detail ? " | " : "") + `Dungeon: ${obj.dungeons.join(", ")}`;
  }
  if (obj.single_session) {
    detail += (detail ? " | " : "") + "Single session";
  }

  return (
    <div className={styles.objRow}>
      <div className={styles.objMain}>
        {icon && (
          <SafeIcon src={icon} alt={label} className={styles.objItemIcon} />
        )}
        <span className={badgeClass}>{type}</span>
        <span
          className={styles.objLabel}
          style={rarityColor ? { color: rarityColor } : undefined}
        >
          {label}
        </span>
        {detail && <span className={styles.objDetail}>{detail}</span>}
      </div>
    </div>
  );
}

function RewardRow({ reward }: { reward: Reward }) {
  const type = reward.type;

  if (type === "Exp") {
    return (
      <div className={styles.rwdRow}>
        <span className={styles.rwdIconStar}>&#9733;</span>
        <span className={styles.rwdText}>
          <span className={styles.rwdCount}>{reward.count}</span> Experience
        </span>
      </div>
    );
  }

  if (type === "Affinity") {
    return (
      <div className={styles.rwdRow}>
        <span className={styles.rwdIconHeart}>&#9829;</span>
        <span className={styles.rwdText}>
          <span className={styles.rwdCount}>{reward.count}</span> Affinity
          {reward.merchant && (
            <span className={styles.rwdMerchant}>
              {" "}({formatId(reward.merchant)})
            </span>
          )}
        </span>
      </div>
    );
  }

  if (type === "Random") {
    const rarityColor = reward.rarity
      ? RARITY_COLORS[reward.rarity]
      : undefined;
    return (
      <div className={styles.rwdRow}>
        <span className={styles.rwdIconRandom}>?</span>
        <span className={styles.rwdText}>
          <span className={styles.rwdCount}>{reward.count}</span>{" "}
          <span style={rarityColor ? { color: rarityColor } : undefined}>
            Random {reward.rarity ?? ""} {reward.item_type ?? "Item"}
          </span>
        </span>
      </div>
    );
  }

  if (type === "Item") {
    const isGold = reward.id === "Id_Item_GoldCoins";
    const icon = reward.id
      ? isGold
        ? "/item-icons/Item_Icon_GoldCoin.png"
        : itemIconUrl(reward.id)
      : null;
    const name = reward.name ?? (reward.id ? formatId(reward.id) : "Item");
    return (
      <div className={styles.rwdRow}>
        {icon ? (
          <SafeIcon src={icon} alt={name} className={styles.rwdItemIcon} />
        ) : (
          <span className={styles.rwdIconGeneric}>&#9670;</span>
        )}
        <span className={styles.rwdText}>
          <span className={styles.rwdCount}>{reward.count}</span> {name}
        </span>
      </div>
    );
  }

  // Stash Tab, Action, Item Skin, Unknown
  return (
    <div className={styles.rwdRow}>
      <span className={styles.rwdIconGeneric}>&#9670;</span>
      <span className={styles.rwdText}>
        <span className={styles.rwdCount}>{reward.count ?? 1}</span> {type}
      </span>
    </div>
  );
}

function QuestCard({
  quest,
  totalQuests,
}: {
  quest: Quest;
  totalQuests: number;
}) {
  return (
    <div className={styles.questCard}>
      {/* Quest number + required level badges */}
      <div className={styles.questChapterBadge}>
        Quest {quest.quest_number} of {totalQuests}
        {quest.required_level > 0 && (
          <span style={{ marginLeft: 12, color: "var(--gold-400)" }}>
            Lv. {quest.required_level}
          </span>
        )}
      </div>

      {/* Title */}
      <h3 className={styles.questTitle}>{quest.title}</h3>

      {/* Greeting text (merchant's words) */}
      {quest.greeting && (
        <p className={styles.questText}>
          &ldquo;{quest.greeting}&rdquo;
        </p>
      )}

      {/* Objectives */}
      {quest.objectives.length > 0 && (
        <div className={styles.questSection}>
          <div className={styles.sectionDivider}>
            <span className={styles.sectionDividerLabel}>Objectives</span>
          </div>
          <div className={styles.objList}>
            {quest.objectives.map((obj, idx) => (
              <ObjectiveRow key={idx} obj={obj} />
            ))}
          </div>
        </div>
      )}

      {/* Rewards */}
      {quest.rewards.length > 0 && (
        <div className={styles.questSection}>
          <div className={styles.sectionDivider}>
            <span className={styles.sectionDividerLabel}>Rewards</span>
          </div>
          <div className={styles.rwdList}>
            {quest.rewards.map((rwd, idx) => (
              <RewardRow key={idx} reward={rwd} />
            ))}
          </div>
        </div>
      )}

      {/* Footer: prereq + dungeons */}
      <div className={styles.questFooter}>
        {quest.prerequisite && (
          <div className={styles.questFooterRow}>
            <span className={styles.footerLabel}>Prerequisite:</span>
            <span className={styles.prereqValue}>
              {quest.prerequisite.title}
            </span>
          </div>
        )}
        {quest.dungeons.length > 0 && (
          <div className={styles.questFooterRow}>
            <span className={styles.footerLabel}>Available Dungeons:</span>
            <div className={styles.dungeonBadges}>
              {quest.dungeons.map((d) => (
                <span key={d} className={styles.dungeonBadge}>
                  {d}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
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

  const totalQuests = useMemo(() => {
    return merchants.reduce((acc, m) => acc + getMerchantQuestCount(m), 0);
  }, [merchants]);

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

  // Chapters sorted by order
  const sortedChapters = useMemo(() => {
    if (!merchant) return [];
    return [...merchant.chapters].sort((a, b) => a.order - b.order);
  }, [merchant]);

  // Total quests for the selected merchant (for "Quest X of Y" display)
  const merchantTotalQuests = useMemo(() => {
    if (!merchant) return 0;
    return getMerchantQuestCount(merchant);
  }, [merchant]);

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
                {merchantTotalQuests} quest
                {merchantTotalQuests !== 1 ? "s" : ""} across{" "}
                {sortedChapters.length} chapter
                {sortedChapters.length !== 1 ? "s" : ""}
              </span>
            </div>
          </div>

          {/* Quest cards grouped by chapter */}
          {sortedChapters.map((chapter) => (
            <div key={chapter.name} className={styles.chapterGroup}>
              <h2 className={styles.chapterTitle}>
                {chapter.name}
                <span
                  style={{
                    marginLeft: 12,
                    fontSize: "0.6875rem",
                    fontWeight: 600,
                    color: "var(--text-muted)",
                    letterSpacing: "0.08em",
                  }}
                >
                  {chapter.quests.length} quest
                  {chapter.quests.length !== 1 ? "s" : ""}
                </span>
              </h2>
              <div className={styles.questGrid}>
                {chapter.quests.map((quest) => (
                  <QuestCard
                    key={quest.id}
                    quest={quest}
                    totalQuests={merchantTotalQuests}
                  />
                ))}
              </div>
            </div>
          ))}

          {sortedChapters.length === 0 && (
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
            {totalQuests} quests across {merchants.length} merchants. Select a
            merchant to browse their quest chain.
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
          <div className={styles.emptyState}>
            No merchants match your search
          </div>
        ) : (
          <div className={styles.merchantGrid}>
            {filteredMerchants.map((m) => {
              const qCount = getMerchantQuestCount(m);
              return (
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
                    {qCount} quest{qCount !== 1 ? "s" : ""}
                  </div>
                  <div className={styles.viewQuestsBtn}>View Quests &rarr;</div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
