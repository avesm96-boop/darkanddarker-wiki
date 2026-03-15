# Website Redesign Progress — 2026-03-13

## Goal
Full website redesign: modern, outstanding, wow-effect. Transform the simple/basic wiki into a premium, visually impressive site.

## Tech Stack
- Next.js 14 (App Router), React 18, CSS Modules + globals.css
- Cinzel / Cinzel Decorative / Inter fonts
- No Tailwind — custom CSS design system

## What's Been Completed

### 1. New Client Components Created
- `website/src/app/components/ScrollReveal.tsx` — IntersectionObserver-based scroll-triggered fade-in animations (configurable direction, delay, distance, duration)
- `website/src/app/components/AnimatedCounter.tsx` — Numbers count up with eased animation when scrolled into view
- `website/src/app/components/GlowCard.tsx` — 3D tilt + mouse-tracking radial glow effect on hover (NOT YET USED on pages — ready for future integration)

### 2. globals.css Complete Rewrite (Design System v2)
Key changes from v1:
- **Glassmorphism variables**: `--glass-bg`, `--glass-border`, `--glass-blur`
- **Darker base colors**: bg-void #040302, bg-deep #0a0806 (slightly darker than before)
- **Better motion**: `--ease: cubic-bezier(0.16, 1, 0.3, 1)` (expo ease-out), added `--ease-out`, `--ease-in`
- **Navbar**: glass blur (20px) with 75% opacity instead of solid
- **Buttons**: `btn-primary` has `animation: gradient-shift` (moving gradient), `btn-outline` is glass
- **Hero**: Added `.hero-grid` animated grid background, bigger title (clamp 3rem-8rem), `title-shimmer` animation
- **Stats bar**: Gradient overlay, taller dividers with gradient
- **Tools grid**: 12-column bento layout via `> *:nth-child(n)` selectors (5/4/3 then 3/4/5 columns)
- **Cards**: Glass bg, 8px border-radius, shine sweep `::after` on hover, top glow `::before`
- **Section labels**: Glass pill badges (border + backdrop-filter)
- **Class cards**: Glass with larger hover (translateY -8px + scale 1.02), portrait zoom on hover
- **Feature items**: Individual glass cards with hover lift
- **Responsive**: Bento grid collapses to 2-col at 1024px, 1-col at 768px

### 3. Homepage (page.tsx) Rewrite
- Hero: 12 ember particles (up from 8), hero-grid element added
- Stats: Uses `AnimatedCounter` component
- Tools: Each card wrapped in `ScrollReveal` with staggered delay (i * 80ms)
- Announcement: Wrapped in `ScrollReveal`
- Classes: Section head and scroll wrapper both use `ScrollReveal` (left direction for the track)
- Features: Each item in `ScrollReveal` with staggered delay (i * 120ms)

## What's NOT Done Yet

### 4. Items Page Redesign (ItemSearch.tsx + items.module.css)
- Extracted all inline styles to CSS Module (`items.module.css`)
- Glass header with pill label, proper title hierarchy
- Wider search input with glass morphism, 12px border-radius, focus glow
- Glass suggestion dropdown with rounded corners, shadow, proper spacing
- Sticky glass filter bar with backdrop-filter blur
- Glass table container (10px border-radius, glass bg)
- Clean table headers with uppercase labels, sort indicators
- Slim probability bars (6px height vs 16px)
- Glass pagination buttons with active state
- All ~850 lines of probability/search logic unchanged

### 6. Monster Detail — Behavior & Strategy Guide System
- Created `website/public/data/guides/ancient-stingray.json` — comprehensive guide data derived from raw game files
- Added GuideData types to MonsterDetail.tsx (phases, attack_categories, combo_flow, status_effects_detail, strategies, elite_differences, ai_perception)
- New "Behavior" tab: overview paragraph, combat phases (numbered cards), attack damage tiers (color-coded by tier), combo flow chains, detailed status effects with counters, AI perception grid
- New "Strategy" tab: priority-sorted strategy cards (critical/high/medium/low with colored borders), elite differences list
- Guide data loaded from `/data/guides/{slug}.json` — falls back gracefully if no guide exists
- Default tab is "Behavior" when guide is available, "Stats" otherwise
- All strategies derived from actual game data: immunity tags, AI decorators, status effect removal conditions, impact resistance values

### Pages Still Needing Redesign
1. **Monster detail** — DONE (glassmorphism CSS + behavior/strategy guide system)
2. **Monsters list** (`/monsters`) — Already has polished table from prior session, may need glass treatment
3. **Classes** (`/classes`) — Stub page, needs full build
4. **Maps** (`/maps`) — Stub page, needs full build
5. **Quests** (`/quests`) — Stub page, needs full build
6. **Market** (`/market`) — Coming soon stub, needs full build

### Bulk Animation Conversion Status
- Loop script running in background, restarts automatically
- As of last check: 19+ monsters converted, 660+ GLB files
- Script: `tools/blender_bulk_convert.py` with `--skip-existing`
- To restart manually: clean incomplete dirs (no manifest.json), then run with --skip-existing

### Components Not Yet Integrated
- `GlowCard.tsx` — 3D tilt card with mouse-tracking glow. Could replace tool-card hover or be used on detail pages.

### Design Decisions Made
- Keep dark fantasy theme but push it with glassmorphism + modern interactions
- Bento grid (asymmetric card sizes) for tools section
- Scroll-triggered animations on all below-fold sections
- Animated counting stats
- Glass morphism as the primary card pattern (not flat cards with corner ornaments)
- 8px border-radius on cards (was 2px)
- Section labels are glass pill badges

### Dev Server
- Run from `darkanddarker-wiki/website`: `npx next dev -p 3000`
- The old `.next` and `out` directories have stale builds — need `npm run build` after redesign

### 5. Bulk Animation Conversion (IN PROGRESS)
- Created `tools/blender_bulk_convert.py` — bulk version of single-monster script
- Auto-discovers all 78 monsters with PSK + PSA files from FModel exports
- Generates kebab-case IDs from filenames, guesses loop behavior from name patterns
- Outputs to `website/public/monster-models/animations/{slug}/` + manifest.json
- Running via: `"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python tools/blender_bulk_convert.py -- --skip-existing`
- Log file: `C:\Users\Administrator\Desktop\DnDMainProject\blender-bulk-convert.log`
- Source: `C:\Users\Administrator\Desktop\New folder (2)\Output\Exports\DungeonCrawler\Content\DungeonCrawler\Characters\Monster`
- Stats: 78 monsters, 3690 PSA files total

## File Paths Modified
- `website/src/app/globals.css` — Complete rewrite
- `website/src/app/page.tsx` — Complete rewrite
- `website/src/app/components/ScrollReveal.tsx` — NEW
- `website/src/app/components/AnimatedCounter.tsx` — NEW
- `website/src/app/components/GlowCard.tsx` — NEW
- `website/src/app/items/ItemSearch.tsx` — Complete rewrite (styles extracted to module)
- `website/src/app/items/items.module.css` — NEW
- `tools/blender_bulk_convert.py` — NEW (bulk animation converter)
- `website/src/app/components/Navbar.tsx` — Unchanged (glass styling via globals.css)
- `website/src/app/components/Footer.tsx` — Unchanged (updated styling via globals.css)
