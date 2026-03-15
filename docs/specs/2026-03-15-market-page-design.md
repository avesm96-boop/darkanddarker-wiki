# Market Page — Design Spec

**Date:** 2026-03-15
**Status:** Approved
**Branch:** dev

## Overview

A full market analytics page for Dark and Darker, powered by the DarkerDB public API (`api.darkerdb.com`). Provides item price search, price history charts, live marketplace listings, and market trend analytics — all client-side with no backend required.

## Data Source

**API:** `https://api.darkerdb.com/v1`
- No API key required (recommended but optional)
- No documented rate limits — use concurrency limiting to be safe (max 5 parallel requests)
- All endpoints return JSON with standard envelope: `{ version, status, code, meta, body }`

### Endpoints Used

| Endpoint | Purpose |
|----------|---------|
| `GET /v1/market` | Current/historical marketplace listings |
| `GET /v1/market/analytics/{item_id}/prices/history` | Aggregated price history (avg/min/max/volume per interval) |
| `GET /v1/items` | Item database (names, IDs, rarities) |
| `GET /v1/population` | Live server population |

### Key Parameters

**Market listings:** `item`, `item_id`, `archetype`, `rarity`, `price` (range), `has_sold`, `has_expired`, `from`, `to`, `order`, `cursor`, `limit` (1-50), `condense`

**Price history:** `from`, `to`, `interval` (15m/1h/4h/1d etc.)

## Architecture

### Page Structure

```
/market
├── page.tsx              — server component, metadata export only
└── MarketPage.tsx        — "use client", all state + rendering
    ├── MarketDashboard   — overview with trending/most-traded/population
    ├── MarketSearch      — search bar with autocomplete
    ├── MarketItemDetail  — price chart + stats for selected item
    └── MarketListings    — filterable table of live listings
```

`page.tsx` is a server component (for metadata). `MarketPage.tsx` gets `"use client"`. This matches the existing pattern (items/page.tsx → ItemSearch, maps/page.tsx → MapExplorer).

### Component Breakdown

#### 1. MarketDashboard (top section)
- **Server Population** — live player count from `/v1/population` (online/lobby/dungeon)
- **Trending Items** — computed client-side: fetch price history for a curated list of ~15 popular items (with concurrency limit of 5), compare current avg vs. 24h ago, show top gainers/losers
- **Most Traded** — items with highest volume from price history data
- **Last Updated** — timestamp showing when data was last fetched
- Layout: 3-4 cards in a row, dark glassmorphism style matching existing design

#### 2. MarketSearch
- Search input with debounced autocomplete
- Autocomplete: use `/v1/items?search=...` server-side search (avoids fetching full item list)
- On selection → loads MarketItemDetail for that item
- Rarity filter pills (Poor → Artifact) for quick filtering

#### 3. MarketItemDetail (appears when item selected)
- **Price chart** — area chart showing price history over time
  - Time range selector: 24h / 7d / 30d
  - Interval per range: 24h → 1h, 7d → 4h, 30d → 1d
  - Shows avg price line, min/max shaded band, volume bars
  - Powered by `/v1/market/analytics/{item_id}/prices/history`
- **Current stats panel** — avg price, min, max, volume (last 24h)
- **Rarity breakdown** — if item has multiple rarities, show price per rarity
- Uses `AbortController` — cancels in-flight requests when user changes selection

#### 4. MarketListings (bottom section)
- Filterable/sortable table of current marketplace listings
- Powered by `/v1/market?item=...&has_sold=false&has_expired=false`
- Columns: Item, Rarity, Price, Quantity, Listed (time ago), Stats/Attributes
- Pagination via cursor-based API
- Filters: rarity dropdown, price range, sort by price/date

### Curated Trending Items

Reduced to ~15 items to limit API calls. Uses item_id (archetype) directly, not display names:

```typescript
const TRENDING_ITEMS = [
  { id: "Longsword", name: "Longsword" },
  { id: "Falchion", name: "Falchion" },
  { id: "Crossbow", name: "Crossbow" },
  { id: "CrystalSword", name: "Crystal Sword" },
  { id: "PlateArmor", name: "Plate Armor" },
  { id: "LightfootBoots", name: "Lightfoot Boots" },
  { id: "WolfPelt", name: "Wolf Pelt" },
  { id: "GoldenKey", name: "Golden Key" },
  { id: "SurgicalKit", name: "Surgical Kit" },
  { id: "BluePotionOfHealing", name: "Blue Potion" },
  { id: "GoldCoinBag", name: "Gold Coin Bag" },
  { id: "TrollBlood", name: "Troll Blood" },
  { id: "CorruptedCrystal", name: "Corrupted Crystal" },
  { id: "Ale", name: "Ale" },
  { id: "Bandage", name: "Bandage" },
];
```

Fetch with concurrency limit of 5. Compare last-6h avg vs. previous-24h avg for trend direction.

## Styling

Follow existing design system:
- Dark glassmorphism (same as monsters/items pages)
- CSS Modules for component-scoped styles
- Color coding: gold for prices, green for price up, red for price down
- Rarity colors from existing globals.css palette
- Font: Cinzel for headings, Inter for data
- Responsive: stack panels vertically on mobile

## Charting

**Library:** Recharts (React-native charting)
- ~200-300KB bundle size — acceptable tradeoff for rich charting capability
- `AreaChart` for price history (avg line with min/max shaded band)
- `BarChart` overlay for volume
- `ResponsiveContainer` for responsive sizing
- Custom tooltip matching our dark theme
- Install: `npm install recharts`

## Data Flow

```
Page Load:
  1. Fetch /v1/population → populate server stats
  2. Fetch trending items price history (5 at a time, concurrency limited)
     → compute trends + most traded
  3. Show dashboard

User searches item:
  1. Debounced search → /v1/items?search=... (server-side search)
  2. On select → cancel any in-flight requests (AbortController)
  3. Fetch /v1/market/analytics/{item_id}/prices/history
  4. Fetch /v1/market?item=...&has_sold=false (live listings)
  5. Render chart + listings
```

## File Structure

```
website/src/app/market/
├── page.tsx              — server component, metadata export
├── MarketPage.tsx        — "use client", main state management
├── MarketDashboard.tsx   — trending items, population, most traded
├── MarketSearch.tsx      — search bar with autocomplete
├── MarketItemDetail.tsx  — price chart + current stats
├── MarketListings.tsx    — filterable listings table
├── market.module.css     — all market page styles
└── api.ts                — DarkerDB API client (fetch wrappers, types)
```

If `market.module.css` exceeds ~300 lines, split into per-component modules.

## Error Handling

- API unavailable → show "Market data temporarily unavailable" banner with retry button
- CORS failure → specific message: "Cannot reach market data service"
- No results → "No listings found for this item"
- Slow response → loading skeleton states (same pattern as monsters page)
- Race conditions → AbortController on user-triggered fetches

## Constraints

- **No backend** — everything runs client-side in the browser
- **No API key** — using public access (add key support later if needed)
- **No caching** — fresh data on every load (browser caching via standard HTTP headers)
- **No user accounts** — no favorites, alerts, or saved searches in v1
- **DarkerDB dependency** — if their API goes down, our market page goes down
- **CORS verified** — tested 2026-03-15, third-party APIs can change this at any time

## Future Enhancements (not in v1)

- Price alerts (needs backend + user accounts)
- Historical comparison across patches
- Item-to-item price correlation
- Personal trade history tracking
- Median price calculation (API only provides avg)
- Switch to lighter charting lib (uplot) if bundle size becomes an issue
