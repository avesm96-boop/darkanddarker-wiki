# Market Page Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a full market analytics page powered by DarkerDB API with price search, history charts, live listings, and trending items dashboard.

**Architecture:** Client-side Next.js page calling DarkerDB API directly from the browser. No backend needed. Recharts for price history visualization. State managed in a single MarketPage client component with sub-components for each section.

**Tech Stack:** Next.js 14 (static export), React 18, Recharts, CSS Modules, DarkerDB API v1

**Spec:** `docs/specs/2026-03-15-market-page-design.md`

---

## File Structure

```
website/src/app/market/
├── page.tsx              — server component, metadata only (replace existing stub)
├── MarketPage.tsx        — "use client", top-level state + layout
├── MarketDashboard.tsx   — population, trending, most traded
├── MarketSearch.tsx      — search input with autocomplete dropdown
├── MarketItemDetail.tsx  — price chart (Recharts) + stats summary
├── MarketListings.tsx    — paginated listings table
├── market.module.css     — all styles
└── api.ts                — typed API client for DarkerDB
```

## Chunk 1: Foundation (API client + page shell)

### Task 1: Install Recharts dependency

**Files:**
- Modify: `website/package.json`

- [ ] **Step 1: Install recharts**

```bash
cd darkanddarker-wiki/website && npm install recharts
```

- [ ] **Step 2: Commit**

```bash
git add package.json package-lock.json
git commit -m "chore: add recharts dependency for market charts"
```

### Task 2: Create DarkerDB API client

**Files:**
- Create: `website/src/app/market/api.ts`

- [ ] **Step 1: Write the API client with types**

```typescript
// api.ts — DarkerDB API client
const API_BASE = "https://api.darkerdb.com/v1";

// ── Types ──────────────────────────────────────────────────────────────

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
    page?: number;
    num_pages?: number;
    total?: number;
    next?: string;
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
  id: number;
  cursor: number;
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
  seller: string | null;
  [key: string]: unknown; // dynamic stat fields like primary_weapon_damage
}

export interface ItemDef {
  id: string;
  archetype: string;
  name: string;
  rarity: string;
  type: string;
  slot_type: string | null;
}

export interface TrendingItem {
  id: string;
  name: string;
  currentAvg: number;
  previousAvg: number;
  changePercent: number;
  volume: number;
}

// ── Fetch helpers ──────────────────────────────────────────────────────

async function apiFetch<T>(path: string, signal?: AbortSignal): Promise<ApiResponse<T>> {
  const res = await fetch(`${API_BASE}${path}`, { signal });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// ── Endpoints ──────────────────────────────────────────────────────────

export async function fetchPopulation(signal?: AbortSignal): Promise<PopulationData> {
  const res = await apiFetch<PopulationData>("/population", signal);
  return res.body;
}

export async function fetchPriceHistory(
  itemId: string,
  interval = "1h",
  from?: string,
  to?: string,
  signal?: AbortSignal,
): Promise<PricePoint[]> {
  let path = `/market/analytics/${encodeURIComponent(itemId)}/prices/history?interval=${interval}`;
  if (from) path += `&from=${encodeURIComponent(from)}`;
  if (to) path += `&to=${encodeURIComponent(to)}`;
  const res = await apiFetch<PricePoint[]>(path, signal);
  return res.body;
}

export async function fetchMarketListings(params: {
  item?: string;
  rarity?: string;
  hasSold?: boolean;
  hasExpired?: boolean;
  order?: "asc" | "desc";
  limit?: number;
  cursor?: number;
}, signal?: AbortSignal): Promise<ApiResponse<MarketListing[]>> {
  const q = new URLSearchParams();
  if (params.item) q.set("item", params.item);
  if (params.rarity) q.set("rarity", params.rarity);
  if (params.hasSold !== undefined) q.set("has_sold", params.hasSold ? "true" : "false");
  if (params.hasExpired !== undefined) q.set("has_expired", params.hasExpired ? "true" : "false");
  if (params.order) q.set("order", params.order);
  if (params.limit) q.set("limit", String(params.limit));
  if (params.cursor) q.set("cursor", String(params.cursor));
  q.set("condense", "true");
  return apiFetch<MarketListing[]>(`/market?${q.toString()}`, signal);
}

export async function searchItems(query: string, signal?: AbortSignal): Promise<ItemDef[]> {
  const res = await apiFetch<ItemDef[]>(`/items?name=${encodeURIComponent(query)}&limit=20`, signal);
  return res.body;
}

// ── Trending computation ───────────────────────────────────────────────

export const TRENDING_ITEMS = [
  { id: "WolfPelt", name: "Wolf Pelt" },
  { id: "GoldenKey", name: "Golden Key" },
  { id: "SurgicalKit", name: "Surgical Kit" },
  { id: "Bandage", name: "Bandage" },
  { id: "Ale", name: "Ale" },
  { id: "GoldCoinBag", name: "Gold Coin Bag" },
  { id: "Longsword", name: "Longsword" },
  { id: "Falchion", name: "Falchion" },
  { id: "Crossbow", name: "Crossbow" },
  { id: "CrystalSword", name: "Crystal Sword" },
  { id: "LightfootBoots", name: "Lightfoot Boots" },
  { id: "PlateArmor", name: "Plate Armor" },
  { id: "Spellbook", name: "Spellbook" },
  { id: "RuggedBoots", name: "Rugged Boots" },
  { id: "Bandage", name: "Bandage" },
];

/** Fetch trending data with concurrency limit */
export async function fetchTrending(signal?: AbortSignal): Promise<TrendingItem[]> {
  const results: TrendingItem[] = [];
  const concurrency = 5;

  for (let i = 0; i < TRENDING_ITEMS.length; i += concurrency) {
    const batch = TRENDING_ITEMS.slice(i, i + concurrency);
    const promises = batch.map(async (item) => {
      try {
        const points = await fetchPriceHistory(item.id, "1h", undefined, undefined, signal);
        if (points.length < 2) return null;

        // Last 6 hours vs previous 24 hours
        const now = new Date();
        const sixHoursAgo = new Date(now.getTime() - 6 * 3600_000);
        const thirtyHoursAgo = new Date(now.getTime() - 30 * 3600_000);

        const recent = points.filter(p => new Date(p.timestamp) >= sixHoursAgo);
        const previous = points.filter(p => {
          const t = new Date(p.timestamp);
          return t >= thirtyHoursAgo && t < sixHoursAgo;
        });

        const recentAvg = recent.length > 0
          ? recent.reduce((s, p) => s + p.avg, 0) / recent.length
          : 0;
        const prevAvg = previous.length > 0
          ? previous.reduce((s, p) => s + p.avg, 0) / previous.length
          : 0;
        const totalVolume = recent.reduce((s, p) => s + p.volume, 0);

        if (prevAvg === 0) return null;

        return {
          id: item.id,
          name: item.name,
          currentAvg: Math.round(recentAvg),
          previousAvg: Math.round(prevAvg),
          changePercent: Math.round(((recentAvg - prevAvg) / prevAvg) * 1000) / 10,
          volume: totalVolume,
        };
      } catch {
        return null;
      }
    });
    const batchResults = await Promise.all(promises);
    results.push(...batchResults.filter((r): r is TrendingItem => r !== null));
  }

  return results;
}
```

- [ ] **Step 2: Commit**

```bash
git add website/src/app/market/api.ts
git commit -m "feat(market): add DarkerDB API client with types"
```

### Task 3: Create page shell and MarketPage component

**Files:**
- Modify: `website/src/app/market/page.tsx` (replace stub)
- Create: `website/src/app/market/MarketPage.tsx`

- [ ] **Step 1: Replace page.tsx stub with metadata wrapper**

```typescript
// page.tsx
import type { Metadata } from "next";
import MarketPage from "./MarketPage";

export const metadata: Metadata = {
  title: "Market — Dark & Darker Tools",
  description: "Live marketplace prices, price history charts, and market trends for Dark and Darker.",
};

export default function MarketRoute() {
  return <MarketPage />;
}
```

- [ ] **Step 2: Create MarketPage.tsx shell**

```typescript
// MarketPage.tsx
"use client";

import { useState, useEffect, useCallback } from "react";
import styles from "./market.module.css";
import { fetchPopulation, fetchTrending, type PopulationData, type TrendingItem } from "./api";

export default function MarketPage() {
  const [population, setPopulation] = useState<PopulationData | null>(null);
  const [trending, setTrending] = useState<TrendingItem[]>([]);
  const [selectedItem, setSelectedItem] = useState<{ id: string; name: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const loadDashboard = useCallback(() => {
    setLoading(true);
    setError(false);
    const controller = new AbortController();

    Promise.all([
      fetchPopulation(controller.signal).then(setPopulation).catch(() => {}),
      fetchTrending(controller.signal).then(setTrending).catch(() => {}),
    ]).finally(() => setLoading(false));

    return () => controller.abort();
  }, []);

  useEffect(() => {
    const cleanup = loadDashboard();
    return cleanup;
  }, [loadDashboard]);

  return (
    <div className={styles.page}>
      <div className={`container ${styles.pageInner}`}>
        <div className="section-head" style={{ marginBottom: "36px" }}>
          <span className="section-label">Economy</span>
          <h1 className="section-title">Market</h1>
          <p className="section-desc">
            Live marketplace data powered by DarkerDB
          </p>
        </div>

        {error && (
          <div className={styles.errorBanner}>
            Market data temporarily unavailable.
            <button onClick={loadDashboard} className={styles.retryBtn}>Retry</button>
          </div>
        )}

        {/* Dashboard will go here */}
        {/* Search will go here */}
        {/* Item detail will go here */}
        {/* Listings will go here */}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create initial market.module.css**

Start with page layout + error styles. Will be expanded in later tasks.

- [ ] **Step 4: Verify build passes**

```bash
cd website && npx next build
```

- [ ] **Step 5: Commit**

```bash
git add website/src/app/market/
git commit -m "feat(market): page shell with API client and dashboard loading"
```

## Chunk 2: Dashboard + Search

### Task 4: Build MarketDashboard component

**Files:**
- Create: `website/src/app/market/MarketDashboard.tsx`
- Modify: `website/src/app/market/market.module.css`
- Modify: `website/src/app/market/MarketPage.tsx` (integrate)

- [ ] **Step 1: Create MarketDashboard with population + trending cards**

Shows:
- Server population (online/lobby/dungeon) in 3 stat cards
- Trending items: top 5 gainers and top 5 losers with % change
- Most traded: top 5 by volume
- "Last updated" timestamp

Props: `{ population, trending, loading }`

Layout: glassmorphism cards matching existing design system. Green text for price up, red for price down.

- [ ] **Step 2: Add dashboard styles to market.module.css**

- [ ] **Step 3: Integrate into MarketPage.tsx**

- [ ] **Step 4: Build + test in browser**

```bash
cd website && npm run dev
```
Visit `/market` — should show population counts and trending items.

- [ ] **Step 5: Commit**

```bash
git add website/src/app/market/
git commit -m "feat(market): dashboard with population and trending items"
```

### Task 5: Build MarketSearch component

**Files:**
- Create: `website/src/app/market/MarketSearch.tsx`
- Modify: `website/src/app/market/market.module.css`
- Modify: `website/src/app/market/MarketPage.tsx` (integrate)

- [ ] **Step 1: Create MarketSearch with debounced autocomplete**

Features:
- Text input with 300ms debounce
- Calls `searchItems(query)` from api.ts
- Shows dropdown with results grouped by archetype (deduped by name)
- On select → calls `onSelect({ id: archetype, name })` prop
- AbortController cancels previous search on new keystroke
- Rarity filter pills below search bar

- [ ] **Step 2: Add search styles**

- [ ] **Step 3: Wire into MarketPage — `selectedItem` state**

When user selects from search → set `selectedItem` which triggers MarketItemDetail render.

- [ ] **Step 4: Build + test autocomplete in browser**

- [ ] **Step 5: Commit**

```bash
git add website/src/app/market/
git commit -m "feat(market): search with debounced autocomplete"
```

## Chunk 3: Item Detail (Chart + Stats)

### Task 6: Build MarketItemDetail with price chart

**Files:**
- Create: `website/src/app/market/MarketItemDetail.tsx`
- Modify: `website/src/app/market/market.module.css`
- Modify: `website/src/app/market/MarketPage.tsx` (integrate)

- [ ] **Step 1: Create MarketItemDetail component**

Props: `{ itemId: string; itemName: string }`

Features:
- Time range selector buttons: 24h / 7d / 30d
- Interval mapping: 24h → "1h", 7d → "4h", 30d → "1d"
- Fetches price history on mount and when range changes
- AbortController for cancellation
- Stats summary: current avg, min, max, 24h volume
- Loading skeleton while fetching

- [ ] **Step 2: Add Recharts price chart**

```typescript
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, ComposedChart } from "recharts";
```

- ComposedChart with:
  - Area for min/max band (shaded, low opacity)
  - Line for avg price
  - Bar for volume (secondary Y axis)
- Custom dark-themed tooltip
- Gold color scheme matching site design
- Responsive container

- [ ] **Step 3: Add item detail styles**

- [ ] **Step 4: Integrate into MarketPage — render when selectedItem is set**

- [ ] **Step 5: Build + test chart rendering**

Select an item from search → chart should render with price history.

- [ ] **Step 6: Commit**

```bash
git add website/src/app/market/
git commit -m "feat(market): item detail with price history chart"
```

## Chunk 4: Listings Table

### Task 7: Build MarketListings component

**Files:**
- Create: `website/src/app/market/MarketListings.tsx`
- Modify: `website/src/app/market/market.module.css`
- Modify: `website/src/app/market/MarketPage.tsx` (integrate)

- [ ] **Step 1: Create MarketListings component**

Props: `{ itemName: string }`

Features:
- Fetches active listings: `/v1/market?item=...&has_sold=false&has_expired=false`
- Sortable columns: Price, Quantity, Listed date
- Rarity badges with color coding (reuse existing rarity colors from globals.css)
- Show item stats (primary/secondary attributes) parsed from dynamic keys
- Cursor-based "Load More" button for pagination
- AbortController
- "Time ago" formatting for created_at

- [ ] **Step 2: Add listings table styles**

Match existing monsters table aesthetic — dark rows, gold headers, hover effects.

- [ ] **Step 3: Integrate into MarketPage below item detail**

- [ ] **Step 4: Build + test pagination**

- [ ] **Step 5: Commit**

```bash
git add website/src/app/market/
git commit -m "feat(market): live marketplace listings table"
```

## Chunk 5: Polish + Push

### Task 8: Final polish and push to dev

- [ ] **Step 1: Verify full build passes**

```bash
cd website && npx next build
```

- [ ] **Step 2: Test all features in dev server**

```bash
npm run dev
```

Verify:
- Dashboard loads with population + trending
- Search autocomplete works
- Item selection shows chart
- Time range switcher works (24h/7d/30d)
- Listings table loads and paginates
- Error states display correctly
- Mobile responsiveness

- [ ] **Step 3: Commit any final fixes**

- [ ] **Step 4: Push dev branch**

```bash
git push origin dev
```

Vercel will create a preview deployment for the dev branch.
