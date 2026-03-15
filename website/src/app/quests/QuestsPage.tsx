"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import styles from "./quests.module.css";

// ---------------------------------------------------------------------------
// Types (matching new quests.json schema)
// ---------------------------------------------------------------------------

interface Objective {
  type: string;
  count?: number;
  target?: string;
  item_id?: string;
  rarity?: string;
  loot_state?: string;
}

interface Reward {
  type: string;
  count?: number;
  item_id?: string;
  rarity?: string;
  item_type?: string;
  merchant_id?: string;
}

interface Quest {
  id: string;
  title: string | null;
  chapter: string | null;
  text: string | null;
  completion_text: string | null;
  dungeons: string[];
  prerequisite: string | null;
  sub_merchant: string;
  objectives: Objective[];
  rewards: Reward[];
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
  source: string;
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

function itemIconUrl(itemId: string): string {
  const base = itemId.replace(/_\d+$/, "");
  return `/item-icons/Item_Icon_${base}.png`;
}

function formatPrereqId(id: string): string {
  // "Alchemist_11" -> "Alchemist #11"
  // "Treasurer_06" -> "Treasurer #06"
  // "TavernMaster_Tuto_03" -> "Tavern Master Tuto #03"
  const m = id.match(/^(.+?)_(\d+)$/);
  if (m) {
    const name = m[1]
      .replace(/([a-z])([A-Z])/g, "$1 $2")
      .replace(/_/g, " ");
    return `${name} #${m[2]}`;
  }
  return id.replace(/([a-z])([A-Z])/g, "$1 $2").replace(/_/g, " ");
}

/** Classify a sub_merchant into a tab category */
function subMerchantCategory(sub: string, merchantName: string): string {
  const lower = sub.toLowerCase();
  if (lower.includes("daily")) return "Daily";
  if (lower.includes("weekly")) return "Weekly";
  if (lower.includes("seasonal")) return "Seasonal";
  // "Final", "Tuto", "Extra", or same as merchant => Story
  return "Story";
}

/** Determine if a merchant needs sub-merchant tabs */
function getMerchantTabs(
  merchant: Merchant
): { label: string; key: string }[] | null {
  const subs = [...new Set(merchant.quests.map((q) => q.sub_merchant))];
  const categories = [...new Set(subs.map((s) => subMerchantCategory(s, merchant.name)))];
  if (categories.length <= 1) return null;

  const order = ["Story", "Daily", "Weekly", "Seasonal"];
  const tabs = order
    .filter((cat) => categories.includes(cat))
    .map((cat) => ({
      label: cat === "Story" ? "Story Quests" : cat,
      key: cat,
    }));

  // Add "All" at front
  tabs.unshift({ label: "All", key: "All" });
  return tabs;
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
  const type = obj.type;
  const badgeClass =
    type === "Kill" || type === "Damage"
      ? styles.objBadgeKill
      : type === "Fetch" || type === "Hold" || type === "Use Item"
      ? styles.objBadgeFetch
      : type === "Explore" || type === "Escape" || type === "Survive"
      ? styles.objBadgeExplore
      : styles.objBadgeGeneric;

  let label = "";
  let detail = "";
  let icon: string | null = null;
  let rarityColor: string | undefined;

  switch (type) {
    case "Kill":
      label = obj.target ? `Kill ${formatId(obj.target)}` : "Kill enemies";
      detail = `Count: ${obj.count ?? "?"}`;
      break;
    case "Fetch":
      label = obj.item_id ? `Fetch ${formatId(obj.item_id)}` : "Fetch items";
      if (obj.item_id) icon = itemIconUrl(obj.item_id);
      if (obj.rarity) {
        label += ` (${obj.rarity})`;
        rarityColor = RARITY_COLORS[obj.rarity];
      }
      detail = `Count: ${obj.count ?? "?"}`;
      if (obj.loot_state) detail += ` | Condition: ${obj.loot_state}`;
      break;
    case "Explore":
      label = obj.target ? `Explore ${formatId(obj.target)}` : "Explore area";
      if (obj.count && obj.count > 1) detail = `Count: ${obj.count}`;
      break;
    case "Escape":
    case "Survive":
      label = `${type} ${obj.count ?? 1} time${(obj.count ?? 1) > 1 ? "s" : ""}`;
      break;
    case "Damage":
      label = obj.target
        ? `Deal damage to ${formatId(obj.target)}`
        : "Deal damage";
      detail = `Amount: ${obj.count ?? "?"}`;
      break;
    case "Hold":
      label = obj.item_id ? `Hold ${formatId(obj.item_id)}` : "Hold items";
      if (obj.item_id) icon = itemIconUrl(obj.item_id);
      detail = `Count: ${obj.count ?? "?"}`;
      break;
    case "Use Item":
      label = obj.item_id
        ? `Use ${formatId(obj.item_id)}`
        : "Use items";
      if (obj.item_id) icon = itemIconUrl(obj.item_id);
      detail = `Count: ${obj.count ?? "?"}`;
      break;
    case "Props":
      label = obj.target
        ? `Interact with ${formatId(obj.target)}`
        : "Interact with props";
      detail = `Count: ${obj.count ?? "?"}`;
      break;
    default:
      label = `${type}`;
      if (obj.count) detail = `Count: ${obj.count}`;
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

  if (type === "Experience") {
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
          {reward.merchant_id && (
            <span className={styles.rwdMerchant}>
              {" "}({formatId(reward.merchant_id)})
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
    const icon = reward.item_id ? itemIconUrl(reward.item_id) : null;
    const name = reward.item_id ? formatId(reward.item_id) : "Item";
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
  merchantName,
}: {
  quest: Quest;
  merchantName: string;
}) {
  const showSubLabel =
    quest.sub_merchant && quest.sub_merchant !== merchantName;

  return (
    <div className={styles.questCard}>
      {/* Chapter badge */}
      {quest.chapter && (
        <div className={styles.questChapterBadge}>
          Chapter: {quest.chapter}
        </div>
      )}

      {/* Sub-merchant label */}
      {showSubLabel && (
        <div className={styles.questSubLabel}>{quest.sub_merchant}</div>
      )}

      {/* Title */}
      <h3 className={styles.questTitle}>
        {quest.title ?? formatPrereqId(quest.id)}
      </h3>

      {/* Quest text */}
      {quest.text && (
        <p className={styles.questText}>&ldquo;{quest.text}&rdquo;</p>
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
              {formatPrereqId(quest.prerequisite)}
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
  const [activeTab, setActiveTab] = useState("All");

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
    return merchants.reduce((acc, m) => acc + m.quest_count, 0);
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

  // Tabs for merchant with sub-types
  const tabs = useMemo(() => {
    if (!merchant) return null;
    return getMerchantTabs(merchant);
  }, [merchant]);

  // Reset tab when changing merchant
  useEffect(() => {
    setActiveTab("All");
  }, [selectedMerchant]);

  // Filter and group quests
  const questChapters = useMemo(() => {
    if (!merchant) return [];

    let quests = merchant.quests;

    // Filter by active tab
    if (tabs && activeTab !== "All") {
      quests = quests.filter(
        (q) => subMerchantCategory(q.sub_merchant, merchant.name) === activeTab
      );
    }

    // Sort: story quests first (by chapter alphabetically, then ID),
    // then daily/weekly/seasonal
    const categoryOrder: Record<string, number> = {
      Story: 0,
      Daily: 1,
      Weekly: 2,
      Seasonal: 3,
    };

    const sorted = [...quests].sort((a, b) => {
      const catA = categoryOrder[subMerchantCategory(a.sub_merchant, merchant.name)] ?? 99;
      const catB = categoryOrder[subMerchantCategory(b.sub_merchant, merchant.name)] ?? 99;
      if (catA !== catB) return catA - catB;
      // Within same category, sort by chapter then by ID
      const chA = a.chapter ?? "";
      const chB = b.chapter ?? "";
      if (chA !== chB) return chA.localeCompare(chB);
      return a.id.localeCompare(b.id);
    });

    // Group by chapter
    const chapters: { name: string; quests: Quest[] }[] = [];
    const chapterMap = new Map<string, Quest[]>();

    for (const q of sorted) {
      const key = q.chapter ?? "Uncategorized";
      let arr = chapterMap.get(key);
      if (!arr) {
        arr = [];
        chapterMap.set(key, arr);
        chapters.push({ name: key, quests: arr });
      }
      arr.push(q);
    }

    return chapters;
  }, [merchant, tabs, activeTab]);

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
    const filteredCount = questChapters.reduce(
      (acc, ch) => acc + ch.quests.length,
      0
    );

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
                {merchant.quests.length} quest
                {merchant.quests.length !== 1 ? "s" : ""}
              </span>
            </div>
          </div>

          {/* Sub-merchant tabs */}
          {tabs && (
            <div className={styles.tabBar}>
              {tabs.map((tab) => (
                <button
                  key={tab.key}
                  className={`${styles.tab} ${
                    activeTab === tab.key ? styles.tabActive : ""
                  }`}
                  onClick={() => setActiveTab(tab.key)}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          )}

          {/* Quest cards grouped by chapter */}
          {questChapters.map((chapter) => (
            <div key={chapter.name} className={styles.chapterGroup}>
              <h2 className={styles.chapterTitle}>{chapter.name}</h2>
              <div className={styles.questGrid}>
                {chapter.quests.map((quest) => (
                  <QuestCard
                    key={quest.id}
                    quest={quest}
                    merchantName={merchant.name}
                  />
                ))}
              </div>
            </div>
          ))}

          {filteredCount === 0 && (
            <div className={styles.emptyState}>
              No quests found for this filter.
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
