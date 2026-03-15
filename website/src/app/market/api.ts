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

/** Curated list of items with confirmed price history data. [archetype, label] */
const CURATED_ITEMS: [string, string][] = [
  ["WolfPelt", "Wolf Pelt"],
  ["WolfClaw", "Wolf Claw"],
  ["GoldCoinPurse", "Gold Coin Purse"],
  ["GoldCoinBag", "Gold Coin Bag"],
  ["SilverCoin", "Silver Coin"],
  ["GoldenTeeth", "Golden Teeth"],
  ["ShiningPearl", "Shining Pearl"],
  ["Lockpick", "Lockpick"],
  ["RottenFluids", "Rotten Fluids"],
  ["BonePowder", "Bone Powder"],
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

export type TrendingRange = "24h" | "7d";

/**
 * Fetch trending data for the curated item list.
 *
 * @param range "24h" compares last 6h vs previous 18h. "7d" compares last 24h vs previous 6d.
 */
export async function fetchTrending(
  range: TrendingRange = "24h",
  signal?: AbortSignal,
): Promise<TrendingItem[]> {
  // For 7d we need more data, use 4h interval
  const interval = range === "7d" ? "4h" : "1h";

  const histories = await mapWithConcurrency(
    CURATED_ITEMS,
    5,
    ([archetype]) => fetchPriceHistory(archetype, interval, signal),
  );

  const now = Date.now();

  // Define "recent" and "previous" windows based on range
  const recentWindow = range === "7d" ? 24 * 3600_000 : 6 * 3600_000;
  const previousEnd = recentWindow;
  const previousWindow = range === "7d" ? 6 * 24 * 3600_000 : 18 * 3600_000;

  const trending: TrendingItem[] = [];

  for (let i = 0; i < CURATED_ITEMS.length; i++) {
    const points = histories[i];
    if (!points || points.length === 0) continue;

    const [archetype, label] = CURATED_ITEMS[i];

    const recent: PricePoint[] = [];
    const previous: PricePoint[] = [];

    for (const p of points) {
      const age = now - new Date(p.timestamp).getTime();
      if (age <= recentWindow) {
        recent.push(p);
      } else if (age <= previousEnd + previousWindow) {
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
    const recentVolume = recent.reduce((s, p) => s + p.volume, 0)
      + previous.reduce((s, p) => s + p.volume, 0);

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
