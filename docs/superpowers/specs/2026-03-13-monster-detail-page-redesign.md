# Monster Detail Page Redesign — Design Spec

## Overview

Redesign the per-monster detail page (`/monsters/[slug]`) from a single-column inline-styled layout into a polished two-panel split layout with tabbed content sections and interactive combo animation playback.

**Reference monster**: Ancient Stingray (`/monsters/ancient-stingray`) — Boss, 2 grades, 39 attacks, 26 combos, 4 status effects, 45 animations.

## Layout Architecture

### Two-Panel Split

```
┌─────────────────────────────────────────────────────────┐
│ ← All Monsters                                          │
├──────────────────────┬──────────────────────────────────┤
│                      │ Ancient Stingray                  │
│                      │ [BOSS] [Beast]  Ship Graveyard    │
│                      │                                   │
│   3D Model Viewer    │ [Common] [Elite]  HP 4000 DMG 38 │
│   (sticky, ~45%)     │─────────────────────────────────  │
│                      │ Stats │ Attacks │ Combos │ Loot │ │
│                      │─────────────────────────────────  │
│                      │                                   │
│                      │ [Tab content scrolls here]        │
│                      │                                   │
└──────────────────────┴──────────────────────────────────┘
```

- **Left panel (~45%)**: 3D model viewer with `position: sticky`. Nearly-square aspect ratio (slightly shorter than square). Stays visible as right panel scrolls.
- **Right panel (~55%)**: All content — identity, grade selector, key stats, and tabbed sections.
- **No separate Animations section** — the Combos tab provides animation playback.
- **Gap**: 28px between panels, 28px page padding.

### Right Panel Structure

1. **Header row**: Monster name (h1), class badge (Boss/Sub-Boss/Normal), creature type tags, dungeon location.
2. **Controls row**: Grade selector buttons + key stats inline (HP, DMG, SPD, XP) separated by a vertical divider.
3. **Horizontal divider**: Thin gradient line.
4. **Tab bar**: Stats | Attacks | Combos | Loot | Abilities
5. **Tab content area**: Scrollable, fills remaining height.

### Tab Content

#### Stats Tab
- **Attributes** (2-column grid): Strength, Vigor, Agility, Dexterity, Will, Knowledge, Resourcefulness.
- **Resistances** (2-column grid): Magic Resistance, all elemental reductions, Impact Resistance, Impact Endurance. Zero values shown dimmed.
- **Status Effects** (2-column grid): Icon + name + tags for each effect.
- **Projectiles & AoE** (inline tags): Labeled badges.

#### Attacks Tab
- List of all attacks with name, damage ratio (%), calculated damage, and impact power.
- Same layout as current but within the tab.

#### Combos Tab
- Each combo shows: **Play button** | from → to
- Clicking Play chains the `from` and `to` animations in the 3D model viewer on the left.
- Animation IDs are provided by the data pipeline (see Data Pipeline section).
- Active combo row is highlighted while playing.

#### Loot Tab
- **Drop table**: Name + quantity for each loot drop.
- **Hunting loot**: Rarity badge, item name, description (italic). Border colored by rarity.

#### Abilities Tab
- Pill-style list of all abilities for the current grade.
- Grade-exclusive abilities highlighted (gold tint + border).
- Footer note: "Highlighted abilities are unique to this grade."
- Only shown when multiple grades exist.

### Grade Comparison
- Shown as a sub-section within the Stats tab (or as its own tab if too long).
- Table comparing all stats across grades. Current grade column highlighted.

## Styling

- **CSS Module** (`MonsterDetail.module.css`) instead of inline styles.
- Follow existing design system variables: `--bg-deep`, `--bg-card`, `--border-dim`, `--gold-*`, `--red-*`, `--font-heading`, `--font-display`, `--font-body`.
- Corner ornaments on the model viewer container (matching `.tableContainer` pattern from monsters list).
- Tab active state: gold text + 2px bottom border.
- Consistent section title style: 8px uppercase, letter-spacing 0.18em, gold-tinted.

## Responsive Behavior

- **Desktop (>1024px)**: Full two-panel split as described.
- **Tablet (768–1024px)**: Reduce gap, slightly smaller model.
- **Mobile (<768px)**: Stack vertically — model on top (16:9 aspect, not sticky), content below. Tabs become horizontally scrollable.

## Data Pipeline Changes

### Combo Animation Mapping

Add an `animation_id` field to each combo entry in `build_monsters.py`:

```json
{
  "from": "TailSlash High",
  "to": "TailAttack Down",
  "from_animation_id": "tail-slash-high",
  "to_animation_id": "tail-attack-down"
}
```

**Mapping logic**: Convert PascalCase combo names to kebab-case animation IDs:
1. `TailSlash High` → `tail-slash-high`
2. `ShortDash` → `short-dash`
3. `WaterArrow 1` → `water-arrow-1`
4. Handle known typos: `TailSlah` → `TailSlash`, `BackSteb` → `BackStep`
5. Validate against the animation manifest; set to `null` if no match found.

### DesignData Filtering

Already implemented in the frontend filter. The pipeline should also skip monsters whose names start with `DesignData` when building the JSON, so the count in the subtitle is accurate at build time.

## 3D Model Viewer Changes

### Combo Playback

The `ModelViewer` component needs a new prop for playing a sequence of animations:

```typescript
interface ComboPlayback {
  animations: string[];  // animation IDs to chain
  onComplete?: () => void;
}
```

When `comboPlayback` is set:
1. Stop any current animation.
2. Play the first animation (non-looping).
3. On completion, play the next animation.
4. On final completion, call `onComplete`.

The combo row in the right panel highlights which step is currently playing.

## Component Structure

```
MonsterDetail.tsx          — main component, state management
MonsterDetail.module.css   — all styles
ModelViewer.tsx             — 3D viewer (existing, add combo playback)
```

No new files needed. The existing `MonsterDetail.tsx` gets rewritten with the new layout, and `ModelViewer.tsx` gets the combo playback feature.

## Out of Scope

- Individual click-to-play on combo attack names (future enhancement).
- Monster image/portrait in the hero area.
- Navigation between monsters (prev/next).
- Search within tabs.
