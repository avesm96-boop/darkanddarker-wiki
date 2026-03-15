# Market Page — Design Spec

**Date:** 2026-03-15
**Status:** Draft
**Branch:** dev

## Overview

A full market analytics page for Dark and Darker, powered by the DarkerDB public API (`api.darkerdb.com`). Provides item price search, price history charts, live marketplace listings, and market trend analytics — all client-side with no backend required.

## Data Source

**API:** `https://api.darkerdb.com/v1`
- No API key required (recommended but optional)
- No documented rate limits
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
/market (page.tsx)
└── MarketPage.tsx (client component)
    ├── MarketDashboard — overview with trending/most-traded/population
    ├── MarketSearch — search bar with autocomplete
    ├── MarketItemDetail — price chart + stats for selected item
    └── MarketListings — filterable table of live listings
```

### Component Breakdown

#### 1. MarketDashboard (top section)
- **Server Population** — live player count from `/v1/population` (online/lobby/dungeon)
- **Trending Items** — computed client-side: fetch price history for a curated list of popular items, compare current avg vs. 24h ago, show top gainers/losers
- **Most Traded** — items with highest volume from price history data
- Layout: 3-4 cards in a row, dark glassmorphism style matching existing design

#### 2. MarketSearch
- Search input with debounced autocomplete
- Autocomplete powered by `/v1/items?search=...` or client-side filter of item list
- On selection → loads MarketItemDetail for that item
- Rarity filter pills (Poor → Artifact) for quick filtering

#### 3. MarketItemDetail (appears when item selected)
- **Price chart** — line/area chart showing price history over time
  - Time range selector: 24h / 7d / 30d
  - Shows avg price line, min/max band, volume bars
  - Powered by `/v1/market/analytics/{item_id}/prices/history`
- **Current stats panel** — avg price, min, max, volume (last 24h)
- **Rarity breakdown** — if item has multiple rarities, show price per rarity

#### 4. MarketListings (bottom section)
- Filterable/sortable table of current marketplace listings
- Powered by `/v1/market?item=...&has_sold=false&has_expired=false`
- Columns: Item, Rarity, Price, Quantity, Listed (time ago), Stats/Attributes
- Pagination via cursor-based API
- Filters: rarity dropdown, price range, sort by price/date

### Curated Trending Items

To compute trends without scanning every item, we use a curated list of ~30 popular tradeable items across categories:

**Weapons:** Longsword, Falchion, Crossbow, Spellbook, Crystal Sword
**Armor:** Plate Armor, Dark Plate Armor, Lightfoot Boots, Rugged Boots
**Materials:** Wolf Pelt, Troll Blood, Corrupted Crystal, Golden Key
**Consumables:** Surgical Kit, Bandage, Blue Potion, Ale
**Valuables:** Gold Coin Bag, Goblet, Ring, Necklace

On page load, fetch price history (1h interval, last 48h) for each. Compare last-6h avg vs. previous-24h avg to determine trend direction and percentage change.

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
- `AreaChart` for price history (avg line with min/max shaded band)
- `BarChart` overlay for volume
- `ResponsiveContainer` for responsive sizing
- Custom tooltip matching our dark theme
- Install: `npm install recharts`

## Data Flow

```
Page Load:
  1. Fetch /v1/population → populate server stats
  2. Fetch /v1/items → cache item list for autocomplete
  3. Fetch price history for curated trending items (parallel) → compute trends

User searches item:
  1. Filter autocomplete from cached item list
  2. On select → fetch /v1/market/analytics/{item_id}/prices/history
  3. On select → fetch /v1/market?item=...&has_sold=false (live listings)
  4. Render chart + listings
```

## File Structure

```
website/src/app/market/
├── page.tsx              — metadata + MarketPage import
├── MarketPage.tsx        — main client component, state management
├── MarketDashboard.tsx   — trending items, population, most traded
├── MarketSearch.tsx      — search bar with autocomplete
├── MarketItemDetail.tsx  — price chart + current stats
├── MarketListings.tsx    — filterable listings table
├── market.module.css     — all market page styles
└── api.ts                — DarkerDB API client (fetch wrappers, types)
```

## Error Handling

- API unavailable → show "Market data temporarily unavailable" banner with retry button
- No results → "No listings found for this item"
- Slow response → loading skeleton states (same pattern as monsters page)
- CORS: DarkerDB API allows cross-origin requests (verified)

## Constraints

- **No backend** — everything runs client-side in the browser
- **No API key** — using public access (add key support later if needed)
- **No caching** — fresh data on every load (browser caching via standard HTTP headers)
- **No user accounts** — no favorites, alerts, or saved searches in v1
- **DarkerDB dependency** — if their API goes down, our market page goes down

## Future Enhancements (not in v1)

- Price alerts (needs backend + user accounts)
- Historical comparison across patches
- Item-to-item price correlation
- Personal trade history tracking
- Median price calculation (API only provides avg)
