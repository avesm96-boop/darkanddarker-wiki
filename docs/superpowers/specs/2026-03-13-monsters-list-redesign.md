# Monsters List Page Redesign — Design Spec

**Sub-project 1 of 3** in the UI overhaul (Monsters List → Monster Detail → Items).

## Goal

Elevate the Monsters List page (`/monsters`) from its current raw-draft table to match the visual quality of the home page, using the existing design system (CSS variables, Cinzel fonts, gold accents, corner ornaments, hover glows).

## Approach: Polished Table

Keep the table format for scan-ability across 152 monsters, but add visual polish: ornamental header, mini portrait circles, styled class badges, row hover glows, alternating row tints, corner ornaments on the container, and a proper page header.

## Page Structure

### Page Header
- Full-width section with dark gradient background (shorter than home hero)
- Title: "Bestiary" in Cinzel Decorative (`var(--font-display)`), matching home page heading style
- Subtitle using existing `section-desc` class pattern
- Subtle gold divider with corner ornaments
- Dynamic monster count badge: `{data.monsters.length} creatures cataloged`

### Filter Bar
- Horizontal bar below header
- **Search input:** Gold-bordered (`var(--border-dim)`), dark background (`var(--bg-raised)`), real-time filtering, placeholder: "Search monsters..."
- **Class filter:** Dropdown — All / Normal / Sub-Boss / Boss
- **Type filter:** Dropdown — All / {dynamically built from creature_types} (keep existing filter)
- **Dungeon filter:** Dropdown
- **Sort:** Clickable column headers in the table header row. Click toggles ascending/descending. Active sort column gets a subtle arrow indicator. Default sort: alphabetical by Name (ascending)
- All controls use existing CSS variables (`var(--bg-raised)`, `var(--border-dim)`, `var(--text-bright)`)
- Focus state on inputs: `border-color: var(--gold-600)` with `box-shadow: 0 0 0 1px var(--gold-800)`

### Table
- Uses div-based CSS grid layout (not semantic `<table>`) for responsive flexibility
- Wrapped in container with `border: 1px solid var(--border-dim)`, `border-radius: 2px`, corner ornaments (::before/::after)
- Container background: `var(--bg-card)` or equivalent subtle warm tint

**Header row:**
- `var(--font-heading)` (Cinzel), `0.625rem`, uppercase, `letter-spacing: 0.14em`, `color: var(--text-muted)`
- Background: `var(--bg-raised)`
- Bottom border: `1px solid var(--border-dim)`
- Columns: Portrait (40px) | Name (1fr) | Class (80px) | Type (90px) | HP (60px) | DMG (60px) | Speed (60px) | Attacks (60px) | Dungeon (auto)
- Sortable columns (Name, HP, DMG, Speed) show cursor: pointer and subtle hover color change

**Data rows:**
- Alternating tint: every other row gets subtle background via `:nth-child(even)`
- Bottom border: `1px solid rgba(201,168,76,0.06)`
- Entire row clickable via `onClick` with `router.push(`/monsters/${slug}`)` — keeps `"use client"` (already present)
- Name cell also has a `<Link>` for SEO/prefetching (stretched via CSS to cover the row for a11y)

**Row content:**
- **Portrait:** 28px circle, `radial-gradient(circle, #2a2418, #151210)`, `border: 1px solid rgba(201,168,76,0.1)`. Placeholder; when images available they slot in.
- **Name:** `var(--font-heading)`, `0.8125rem`, `color: var(--gold-300)`, `letter-spacing: 0.04em`
- **Class badges:** Use existing `CLASS_COLORS` map from current page:
  - Boss: `bg: var(--red-900)`, `border: var(--red-700)`, `color: var(--red-300)`
  - Sub-Boss: `bg: var(--gold-950)`, `border: var(--gold-800)`, `color: var(--gold-500)`
  - Normal: `bg: var(--bg-raised)`, `border: var(--border-dim)`, `color: var(--text-dim)`
- **Type:** `var(--font-body)`, `0.75rem`, `color: var(--text-dim)`
- **Stats (HP, DMG, Speed):** `var(--font-body)`, `0.8125rem`, `color: var(--text-bright)` when > 0, `var(--text-muted)` with "—" when 0
- **Attacks:** Count number, `color: var(--text-dim)`, "—" if none
- **Dungeon:** `var(--font-body)`, `0.75rem`, `color: var(--text-dim)`

## Interactions

### Row Hover
- Background: `var(--bg-card-h)` (existing hover variable)
- Left accent: `box-shadow: inset 3px 0 0 rgba(201,168,76,0.4)`
- Cursor: pointer
- Name text color shifts to `var(--gold-100)`

### Row Click
- Navigate to `/monsters/[slug]` via `router.push()`
- Active state (`:active`): `background: rgba(201,168,76,0.08)` — brief brighten on press

### Search
- Real-time filtering as user types (existing behavior)
- Empty state: "No creatures match your search" in `var(--font-heading)`, `var(--text-muted)`, centered

### Loading State
- Skeleton rows: 8 rows of animated placeholder bars (pulse-glow animation from globals.css)
- Uses same grid layout as real rows, with grey gradient bars in place of text

### Error State
- Centered message: "Failed to load bestiary data" with a "Retry" button
- Same styling as empty state

### Load Animation
- Staggered `fade-in-up` on first 20 rows using inline `style={{ animationDelay: `${index * 30}ms` }}`
- Remaining rows (`index >= 20`) have no animation delay — appear instantly

## Responsive Behavior

### Desktop (>1024px)
- Full grid with all 9 columns
- Filter bar in one horizontal row

### Tablet (768–1024px)
- Hide Speed and Attacks columns via CSS (`display: none` on those grid cells)
- Compact padding on cells

### Mobile (<768px)
- Grid switches to a stacked card-list layout via CSS media query
- Each monster: horizontal row card with portrait circle, name, class badge, HP
- Name and class badge on one line, HP below
- No horizontal scrolling
- Search full-width on top
- Filter dropdowns collapse into a "Filters" toggle button that reveals them vertically

## Technical Notes

- Keep client-side rendering with existing `/data/monsters.json` fetch
- No pagination needed (152 items renders fine)
- No virtual scrolling needed at this count
- Use CSS variables from `globals.css` wherever possible — avoid hardcoded hex values
- Use `var(--font-heading)` for Cinzel, `var(--font-display)` for Cinzel Decorative
- Div-based grid layout enables responsive column hiding and mobile card switch without duplicate markup
- Corner ornaments use the same `::before`/`::after` pattern as `.tool-card` in globals.css

## File Changes

1. `website/src/app/monsters/page.tsx` — Full rewrite of markup and styles
2. `website/src/app/monsters/monsters.module.css` — New CSS module for the page (extract from inline styles)
3. No data pipeline changes — same `monsters.json` schema
