# Monster Extended Data — Design Spec

## Goal
Add all available game data to monster pages: combo chains, status effects (with icons), loot drops, hunting loot, AI behavior, projectiles, and AoE details. Split per-variant (Common/Elite/Nightmare).

## Data Sources

| Data | Source Path | Format |
|------|-----------|--------|
| Combo chains | `raw/.../Characters/Monster/{Name}/GameplayAbility/Combo/` | Filenames encode transitions: `GA_{Monster}_{Attack}_From_{Source}.json` |
| Status effects | `raw/.../ActorStatus/Debuff/Monster/{Name}/` + UIData JSONs | UIData has icon texture name, GE_ has effect tags/duration |
| Status icons | `raw/.../UI/Resources/IconActorStatus/*.png` | 70x70 PNGs, 430 total |
| Loot drops | `raw/.../V2/LootDrop/LootDropGroup/ID_LootdropGroup_{Name}.json` | Drop tables with item refs and quantities |
| Hunting loot | `extracted/items/` cross-referenced with monster name | Item data with description, rarity, icon |
| AI behavior | `raw/.../Characters/Monster/{Name}/BT_{Name}.json` + BTD decorators | Range thresholds, attack selection |
| Projectiles | `raw/.../Characters/Monster/{Name}/BP_{Name}_*.json` | Projectile type, physics |
| AoE | `extracted/combat/Id_Aoe_{Name}_*.json` | AoE definitions |
| Per-variant abilities | `raw/.../V2/Monster/Monster/Id_Monster_{Name}_{Grade}.json` | Abilities array differs per grade |

## Data Pipeline Changes (`build_monsters.py`)

### New fields in `monsters.json` per-monster:

```json
{
  "slug": "ancient-stingray",
  "name": "Ancient Stingray",
  "combos": [
    { "from": "TailSlash High", "to": "TailAttack Down" },
    { "from": "TailSlash High", "to": "WaterArrow 1" },
    { "from": "ShortDash", "to": "TailSlash High" }
  ],
  "status_effects": [
    {
      "name": "Tail Poison",
      "icon": "Icon_Debuff_Poison",
      "duration_ms": 30000,
      "tags": ["Debuff", "Poison"],
      "description": "Poisoned by tail attack"
    },
    {
      "name": "Dash Stun",
      "icon": "Icon_Debuff_Trapped",
      "duration_ms": null,
      "tags": ["Debuff", "Trapped", "Silence"],
      "description": "Stunned by dash impact"
    }
  ],
  "loot": [
    { "name": "Boss Loot", "quantity": 3 },
    { "name": "Corroded Key", "quantity": 1 }
  ],
  "hunting_loot": {
    "name": "Ancient Stingray Egg",
    "rarity": "Epic",
    "description": "An egg with a thick, leathery shell..."
  },
  "projectiles": [
    { "name": "Water Arrow", "type": "Physical" },
    { "name": "Rock", "type": "Physical" }
  ],
  "aoe": [
    { "name": "Lightning Bubble", "type": "Magical" }
  ],
  "ai_behavior": {
    "ranges": { "swim": "10-15m", "turning_attack": "close" },
    "notes": "Randomized attack selection, swims at 10m and 15m ranges"
  },
  "grades": {
    "Common": {
      "abilities": ["TailSlash", "TailAttack", "ShortDash", "Rush", "WaterArrow", "LightningNova", "DivineJudgment", "LightningBubble"],
      "stats": { ... }
    },
    "Elite": {
      "abilities": ["...same + LightningBubble_Elite", "Rush_FallingRock"],
      "stats": { ... }
    }
  }
}
```

### Icon Pipeline

1. Build script copies referenced status effect PNGs from `raw/.../IconActorStatus/` to `website/public/icons/status/`
2. Icons served at `/icons/status/Icon_Debuff_Poison.png`
3. Small files (70x70) — no resizing needed

## UI Sections (added to MonsterDetail.tsx)

Order on the page (after existing sections):

1. **Status Effects** — Grid of effect cards with icon (70x70), name, duration, tags
2. **Combo Chains** — Visual flow diagram or table showing attack → follow-up transitions
3. **Loot Drops** — Simple list with quantity badges
4. **Hunting Loot** — Card with rarity border color, description, icon if available
5. **Projectiles & AoE** — Combined section, simple cards with type badges
6. **AI Behavior** — Condensed info: engagement ranges, attack pattern notes

## Variant Splitting

- Status effects: shared across variants (same debuffs)
- Abilities list: per-grade (Elite has extra abilities)
- Attacks table (existing): already grade-aware via damage calc from grade stats
- Combos: shared (same skeleton, different abilities available)
- Loot: may differ per grade (check spawner data)

## File Changes

1. `tools/build_monsters.py` — Add extraction for all new data types
2. `website/public/data/monsters.json` — Extended schema
3. `website/src/app/monsters/[slug]/MonsterDetail.tsx` — New UI sections
4. `website/public/icons/status/` — Copied icon PNGs (build step)
