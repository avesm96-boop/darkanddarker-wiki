// DarkerDB API Client
// Base URL: https://api.darkerdb.com/v1

// Use Vercel proxy to avoid CORS issues (DarkerDB API has no CORS headers)
const BASE = "/api/darkerdb/v1";
const API_KEY = "6f45b5a13f622bbe0f37";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ApiResponse<T> {
  version: string;
  status: string;
  code: number;
  query_time: number;
  body: T;
  pagination?: {
    count: number;
    limit: number;
    cursor?: number;
  };
}

export interface PopulationData {
  timestamp: string;
  num_online: number;
  num_lobby: number;
  num_dungeon: number;
}

export interface PricePoint {
  timestamp: string;
  item_id: string;
  avg: number;
  min: number;
  max: number;
  volume: number;
}

export interface MarketListing {
  id: string;
  cursor: string;
  item_id: string;
  item: string;
  archetype: string;
  rarity: string;
  price: number;
  price_per_unit: number;
  quantity: number;
  created_at: string;
  expires_at: string;
  has_sold: boolean;
  has_expired: boolean;
  seller: string;
  /** Listings carry dynamic stat fields (e.g. primary_weapon_damage). */
  [stat: string]: unknown;
}

export interface ItemDef {
  id: string;
  archetype: string;
  name: string;
  rarity: string;
  type: string;
  slot_type: string;
  description: string;
  [key: string]: unknown;
}

export interface TrendingItem {
  archetype: string;
  label: string;
  currentAvg: number;
  previousAvg: number;
  changePct: number;
  recentVolume: number;
}

// ---------------------------------------------------------------------------
// Fetch helpers
// ---------------------------------------------------------------------------

async function get<T>(
  path: string,
  params?: Record<string, string | number>,
  signal?: AbortSignal,
): Promise<T> {
  const qs = new URLSearchParams();
  qs.set("key", API_KEY);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      qs.set(k, String(v));
    }
  }
  const qsStr = qs.toString();
  const url = `${BASE}${path}${qsStr ? `?${qsStr}` : ""}`;

  const res = await fetch(url, {
    signal,
    headers: { Accept: "application/json" },
  });

  if (!res.ok) {
    throw new Error(`DarkerDB ${res.status}: ${res.statusText} – ${path}`);
  }

  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Endpoint functions
// ---------------------------------------------------------------------------

/** Fetch current population snapshot. */
export async function fetchPopulation(
  signal?: AbortSignal,
): Promise<PopulationData> {
  const res = await get<ApiResponse<PopulationData>>(
    "/population",
    undefined,
    signal,
  );
  return res.body;
}

/**
 * Fetch price history for an item archetype.
 *
 * @param archetype  e.g. "Longsword", "WolfPelt" (NOT item_id like "Longsword_5001")
 * @param interval   bucket size, e.g. "1h", "6h", "1d"
 */
export async function fetchPriceHistory(
  archetype: string,
  interval: string = "1h",
  signal?: AbortSignal,
): Promise<PricePoint[]> {
  const res = await get<ApiResponse<PricePoint[]>>(
    `/market/analytics/${encodeURIComponent(archetype)}/prices/history`,
    { interval },
    signal,
  );
  return res.body ?? [];
}

/**
 * Fetch market listings for an item.
 *
 * @param item     Human-readable item name, e.g. "Longsword"
 * @param limit    Max results (default 20)
 * @param condense Merge similar listings (default true)
 */
export async function fetchMarketListings(
  item: string,
  limit: number = 20,
  condense: boolean = true,
  signal?: AbortSignal,
): Promise<MarketListing[]> {
  const res = await get<ApiResponse<MarketListing[]>>("/market", {
    item,
    limit,
    condense: condense ? "true" : "false",
  }, signal);
  return res.body ?? [];
}

/**
 * Search the item definitions catalogue.
 *
 * @param name   Partial or full item name filter
 * @param limit  Max results (default 20)
 */
export async function searchItems(
  name: string,
  limit: number = 20,
  signal?: AbortSignal,
): Promise<ItemDef[]> {
  const res = await get<ApiResponse<ItemDef[]>>("/items", {
    name,
    limit,
  }, signal);
  return res.body ?? [];
}

// ---------------------------------------------------------------------------
// Trending computation
// ---------------------------------------------------------------------------

/** Curated list of popular items to track for trending. [archetype, label] */
const CURATED_ITEMS: [string, string][] = [
  ["Longsword", "Longsword"],
  ["RondelDagger", "Rondel Dagger"],
  ["CrystalBall", "Crystal Ball"],
  ["SpellBook", "Spell Book"],
  ["WolfPelt", "Wolf Pelt"],
  ["GoblinEar", "Goblin Ear"],
  ["GoldCoinPurse", "Gold Coin Purse"],
  ["RubyGem", "Ruby"],
  ["GoldIngot", "Gold Ingot"],
  ["BluePotion", "Blue Potion"],
  ["SurgicalKit", "Surgical Kit"],
  ["Bandage", "Bandage"],
  ["Hatchet", "Hatchet"],
  ["Crossbow", "Crossbow"],
  ["PlateArmor", "Plate Armor"],
];

/**
 * Run `fn` for every item in `items`, at most `concurrency` at a time.
 * Returns results in the same order; failed items resolve to `null`.
 */
async function mapWithConcurrency<T, R>(
  items: T[],
  concurrency: number,
  fn: (item: T) => Promise<R>,
): Promise<(R | null)[]> {
  const results: (R | null)[] = new Array(items.length).fill(null);
  let cursor = 0;

  async function worker() {
    while (cursor < items.length) {
      const idx = cursor++;
      try {
        results[idx] = await fn(items[idx]);
      } catch {
        results[idx] = null;
      }
    }
  }

  const workers: Promise<void>[] = [];
  for (let i = 0; i < Math.min(concurrency, items.length); i++) {
    workers.push(worker());
  }
  await Promise.all(workers);
  return results;
}

/**
 * Fetch trending data for the curated item list.
 *
 * Compares the average price over the last 6 hours against the previous 24
 * hours and returns items sorted by absolute change percentage (descending).
 */
export async function fetchTrending(
  signal?: AbortSignal,
): Promise<TrendingItem[]> {
  const histories = await mapWithConcurrency(
    CURATED_ITEMS,
    5,
    ([archetype]) => fetchPriceHistory(archetype, "1h", signal),
  );

  const now = Date.now();
  const SIX_HOURS = 6 * 60 * 60 * 1000;
  const TWENTY_FOUR_HOURS = 24 * 60 * 60 * 1000;

  const trending: TrendingItem[] = [];

  for (let i = 0; i < CURATED_ITEMS.length; i++) {
    const points = histories[i];
    if (!points || points.length === 0) continue;

    const [archetype, label] = CURATED_ITEMS[i];

    // Split points into recent (0-6h) and previous (6-24h) buckets.
    const recent: PricePoint[] = [];
    const previous: PricePoint[] = [];

    for (const p of points) {
      const age = now - new Date(p.timestamp).getTime();
      if (age <= SIX_HOURS) {
        recent.push(p);
      } else if (age <= TWENTY_FOUR_HOURS) {
        previous.push(p);
      }
    }

    if (recent.length === 0 || previous.length === 0) continue;

    const avg = (pts: PricePoint[]) =>
      pts.reduce((s, p) => s + p.avg, 0) / pts.length;

    const currentAvg = avg(recent);
    const previousAvg = avg(previous);

    if (previousAvg === 0) continue;

    const changePct = ((currentAvg - previousAvg) / previousAvg) * 100;
    const recentVolume = recent.reduce((s, p) => s + p.volume, 0);

    trending.push({
      archetype,
      label,
      currentAvg,
      previousAvg,
      changePct,
      recentVolume,
    });
  }

  // Sort by absolute change descending.
  trending.sort((a, b) => Math.abs(b.changePct) - Math.abs(a.changePct));

  return trending;
}
