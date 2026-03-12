# Pipeline — Data Extraction Scripts

Each script reads raw FModel JSON exports from `raw/` and writes normalized data to `extracted/`. Scripts are independent and can be run in any order.

## Scripts

### Priority 1 — Core Game Data

| Script | Output | Description |
|--------|--------|-------------|
| `extract_items.py` | `extracted/items/` | Parses weapon, armor, accessory, and consumable DataTables. Normalizes stat blocks, rarity tiers, slot types, and item properties into a flat per-item JSON schema. |
| `extract_classes.py` | `extracted/classes/` | Extracts class definitions including base stats, stat scaling, perks, skills, and spells. Resolves cross-references to items (e.g., starting equipment). |
| `extract_monsters.py` | `extracted/monsters/` | Pulls mob definitions — health, damage, resistances, movement speed, aggro range. Links loot drop tables from item data. |

### Priority 2 — Mechanics & Economy

| Script | Output | Description |
|--------|--------|-------------|
| `extract_gameplay.py` | `extracted/gameplay/` | Extracts status effects, damage formulas, interaction speeds, buff/debuff definitions, and other core mechanics data. |
| `extract_economy.py` | `extracted/economy/` | Parses merchant inventories, buy/sell price tables, and crafting recipes. References item IDs from `extracted/items/`. |

### Priority 3 — World & Engine

| Script | Output | Description |
|--------|--------|-------------|
| `extract_maps.py` | `extracted/maps/` | Processes dungeon module layouts, extraction portal positions, shrine locations, and spawn point data from map assets. |
| `extract_engine.py` | `extracted/engine/` | Dumps internal enums, asset path mappings, and ID-to-name resolution tables used by other scripts as reference data. |

## Running

```bash
# From the repo root:
npm run pipeline              # Run all extractors in dependency order
npm run pipeline:items        # Run a single extractor

# Or directly:
python pipeline/extract_items.py
```

## Adding a New Extractor

1. Create `pipeline/extract_<domain>.py`
2. Read from `raw/` using the helpers in `pipeline/utils.py`
3. Write output to `extracted/<domain>/`
4. Add an npm script in the root `package.json`
5. Add a row to the table above
6. Run it and commit the resulting `extracted/` output

## Conventions

- **One file per entity** in `extracted/` (e.g., `extracted/items/longsword.json`)
- **Snake_case keys** in all output JSON
- **IDs are slugified names** (e.g., `crystal_sword`, `skeleton_archer`)
- Every output file includes a `_meta` field with extraction timestamp and source path
- Scripts must be idempotent — running twice produces identical output
