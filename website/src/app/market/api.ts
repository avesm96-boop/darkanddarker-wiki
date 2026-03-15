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
  avg14d: number;
  avg7d: number;
  avg24h: number;
  currentAvg: number;      // last 6h avg
  currentLowest: number;   // lowest price_per_unit in recent listings
  previousAvg: number;     // for change calc
  changePct: number;
  totalVolume: number;
  priceHistory: PricePoint[];  // raw points for mini chart
}

// ---------------------------------------------------------------------------
// Icon helpers
// ---------------------------------------------------------------------------

const ICON_OVERRIDES: Record<string, string> = {
  RottenFluids: "RottenFluides",
  ShiningPearl: "PearlNecklace",
  GoldCoinBag: "CoinBag",
  GoldenTeeth: "GoldenTeeth",
};

export function itemIconPath(archetype: string): string {
  const name = ICON_OVERRIDES[archetype] ?? archetype;
  return `/item-icons/Item_Icon_${name}.png`;
}
export const GOLD_ICON = "/item-icons/Item_Icon_GoldCoin.png";

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

/**
 * Fetch trending data for the curated item list.
 * Uses 4h interval for ~7 days of data, computes all time windows.
 */
export async function fetchTrending(
  signal?: AbortSignal,
): Promise<TrendingItem[]> {
  const interval = "4h";

  // Fetch price histories and lowest listings concurrently
  const [histories, listings] = await Promise.all([
    mapWithConcurrency(
      CURATED_ITEMS,
      5,
      ([archetype]) => fetchPriceHistory(archetype, interval, signal),
    ),
    mapWithConcurrency(
      CURATED_ITEMS,
      5,
      ([, label]) => fetchMarketListings(label, 1, true, signal),
    ),
  ]);

  const now = Date.now();

  const trending: TrendingItem[] = [];

  for (let i = 0; i < CURATED_ITEMS.length; i++) {
    const points = histories[i];
    if (!points || points.length === 0) continue;

    const [archetype, label] = CURATED_ITEMS[i];

    // Sort points chronologically
    const sorted = [...points].sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
    );

    // Compute averages by slicing from the end (most recent data)
    // With 4h intervals: 6 pts ≈ 24h, 42 pts ≈ 7d, all pts ≈ 14d
    const avg = (arr: PricePoint[]) =>
      arr.length === 0 ? 0 : arr.reduce((s, p) => s + p.avg, 0) / arr.length;

    const avg14d = avg(sorted);
    const avg7d = avg(sorted.slice(-42));     // last ~7 days
    const avg24h = avg(sorted.slice(-6));     // last ~24 hours
    const currentAvg = avg(sorted.slice(-2)); // last ~8 hours (most recent)

    // Change: compare most recent vs the period before it
    const recentSlice = sorted.slice(-3);      // last ~12h
    const previousSlice = sorted.slice(-9, -3); // 12-36h ago
    const previousAvg = avg(previousSlice);

    if (sorted.length < 4) continue;

    if (previousAvg === 0) continue;

    const changePct = previousAvg > 0 ? ((currentAvg - previousAvg) / previousAvg) * 100 : 0;
    const totalVolume = sorted.reduce((s, p) => s + p.volume, 0);

    // Get lowest listing price
    const itemListings = listings[i];
    const currentLowest = itemListings && itemListings.length > 0
      ? itemListings[0].price_per_unit
      : 0;

    trending.push({
      archetype,
      label,
      avg14d,
      avg7d,
      avg24h,
      currentAvg,
      currentLowest,
      previousAvg,
      changePct,
      totalVolume,
      priceHistory: points,
    });
  }

  // Sort by absolute change descending.
  trending.sort((a, b) => Math.abs(b.changePct) - Math.abs(a.changePct));

  return trending;
}
