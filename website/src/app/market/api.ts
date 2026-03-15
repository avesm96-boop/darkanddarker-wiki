// Marketplace API Client — powered by our own Hetzner poller
// Replaces DarkerDB dependency with direct game server data

const OUR_API = "http://5.161.247.74:8080/api/v1";

// Keep DarkerDB for population only (we don't track this)
const DARKERDB_BASE = "/api/darkerdb/v1";
const DARKERDB_KEY = "6f45b5a13f622bbe0f37";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

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
  currentAvg: number;
  currentLowest: number;
  previousAvg: number;
  changePct: number;
  totalVolume: number;
  priceHistory: PricePoint[];
}

export interface CleanPricePoint extends PricePoint {
  typical: number;
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

async function ourGet<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`${OUR_API}${path}`, {
    signal,
    headers: { Accept: "application/json" },
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Population (still from DarkerDB — we don't track this)
// ---------------------------------------------------------------------------

interface DarkerDBResponse<T> {
  body: T;
}

export async function fetchPopulation(
  signal?: AbortSignal,
): Promise<PopulationData> {
  try {
    const qs = new URLSearchParams({ key: DARKERDB_KEY });
    const res = await fetch(`${DARKERDB_BASE}/population?${qs}`, {
      signal,
      headers: { Accept: "application/json" },
    });
    if (!res.ok) throw new Error("DarkerDB unavailable");
    const data = (await res.json()) as DarkerDBResponse<PopulationData>;
    return data.body;
  } catch {
    // Fallback if DarkerDB is down
    return { timestamp: new Date().toISOString(), num_online: 0, num_lobby: 0, num_dungeon: 0 };
  }
}

// ---------------------------------------------------------------------------
// Listings — from our API
// ---------------------------------------------------------------------------

interface OurListingsResponse {
  listings: Array<{
    listing_id: number;
    item_id: string;
    item_base_name: string;
    item_marketplace_id: string;
    item_count: number;
    rarity: number;
    rarity_name: string;
    price: number;
    seller_name: string;
    seller_info: string;
    listing_time: number;
    first_seen_at: number;
    last_seen_at: number;
    sold_at: number | null;
    status: string;
    properties: Array<{
      property_type: string;
      property_value: number;
      is_primary: number;
    }>;
  }>;
  count: number;
}

function adaptListing(l: OurListingsResponse["listings"][0]): MarketListing {
  const listing: MarketListing = {
    id: String(l.listing_id),
    cursor: String(l.listing_id),
    item_id: l.item_id,
    item: l.item_base_name,
    archetype: l.item_base_name,
    rarity: l.rarity_name,
    price: l.price,
    price_per_unit: l.price / Math.max(l.item_count, 1),
    quantity: l.item_count,
    created_at: new Date(l.first_seen_at * 1000).toISOString(),
    expires_at: "",
    has_sold: l.status === "sold",
    has_expired: false,
    seller: l.seller_name || "Anonymous",
  };

  // Flatten properties as dynamic stat keys
  for (const prop of l.properties) {
    const name = prop.property_type
      .replace("Id_ItemPropertyType_Effect_", "")
      .replace(/([A-Z])/g, " $1")
      .trim();
    listing[name] = prop.property_value;
  }

  return listing;
}

export async function fetchMarketListings(
  item: string,
  limit: number = 20,
  _condense: boolean = true,
  signal?: AbortSignal,
  price?: string,
): Promise<MarketListing[]> {
  let path = `/listings?item=${encodeURIComponent(item)}&limit=${limit}`;
  if (price) path += `&price_min=${price}`;
  const data = await ourGet<OurListingsResponse>(path, signal);
  return data.listings.map(adaptListing);
}

// ---------------------------------------------------------------------------
// Price History — from our API
// ---------------------------------------------------------------------------

interface OurHistoryResponse {
  history: Array<{
    timestamp: number;
    active_count: number;
    min_price: number;
    max_price: number;
    median_price: number;
    avg_price: number;
    p10_price: number;
    p25_price: number;
    p75_price: number;
    p90_price: number;
  }>;
  count: number;
}

export async function fetchPriceHistory(
  archetype: string,
  _interval: string = "1h",
  signal?: AbortSignal,
): Promise<PricePoint[]> {
  const hours = _interval === "1d" ? 720 : _interval === "4h" ? 168 : 24;
  const data = await ourGet<OurHistoryResponse>(
    `/prices/history?item=${encodeURIComponent(archetype)}&hours=${hours}`,
    signal,
  );

  return data.history.map((h) => ({
    timestamp: new Date(h.timestamp * 1000).toISOString(),
    item_id: archetype,
    avg: h.avg_price || 0,
    min: h.min_price || 0,
    max: h.max_price || 0,
    volume: h.active_count || 0,
  }));
}

// ---------------------------------------------------------------------------
// Item Search — from our API
// ---------------------------------------------------------------------------

interface OurItemsResponse {
  items: Array<{
    marketplace_id: string;
    name: string;
    item_type: string;
    slot_type: string;
    armor_type: string;
  }>;
  count: number;
}

export async function searchItems(
  name: string,
  limit: number = 20,
  signal?: AbortSignal,
): Promise<ItemDef[]> {
  const data = await ourGet<OurItemsResponse>(
    `/items?search=${encodeURIComponent(name)}&limit=${limit}`,
    signal,
  );

  return data.items.map((item) => ({
    id: item.marketplace_id,
    archetype: item.marketplace_id.replace("Id.Item.", ""),
    name: item.name,
    rarity: "",
    type: item.item_type,
    slot_type: item.slot_type || "",
    description: "",
  }));
}

// ---------------------------------------------------------------------------
// Trending — from our API
// ---------------------------------------------------------------------------

interface OurTrendingResponse {
  items: Array<{
    marketplace_id: string;
    name: string;
    active_count: number;
    sold_count: number;
    min_price: number;
    max_price: number;
    avg_price: number;
    price_history: Array<{
      timestamp: number;
      avg_price: number;
      min_price: number;
      max_price: number;
      active_count: number;
    }>;
  }>;
}

export async function fetchTrending(
  signal?: AbortSignal,
): Promise<TrendingItem[]> {
  const data = await ourGet<OurTrendingResponse>("/trending", signal);

  return data.items
    .filter((item) => item.active_count > 0)
    .slice(0, 30)
    .map((item) => {
      const archetype = item.marketplace_id.replace("Id.Item.", "");
      const history = item.price_history || [];

      const priceHistory: PricePoint[] = history.map((h) => ({
        timestamp: new Date(h.timestamp * 1000).toISOString(),
        item_id: archetype,
        avg: h.avg_price || 0,
        min: h.min_price || 0,
        max: h.max_price || 0,
        volume: h.active_count || 0,
      }));

      return {
        archetype,
        label: item.name,
        avg14d: item.avg_price,
        avg7d: item.active_count,    // Used by dashboard as "Listings" count
        avg24h: item.avg_price,
        currentAvg: Math.round(item.avg_price),
        currentLowest: item.min_price,
        previousAvg: item.avg_price,
        changePct: 0, // Will be meaningful once we have enough historical data
        totalVolume: item.sold_count,
        priceHistory,
      };
    });
}
