# Full Game Data Extraction Pipeline — Design Spec

**Date:** 2026-03-12
**Project:** darkanddarker-wiki
**Scope:** Complete extraction of all Dark and Darker UE5 game systems into wiki-optimized JSON
**Status:** Approved

---

## 1. Purpose

Build a complete data extraction pipeline that reads all raw FModel-exported UE5 JSON assets from `raw/` and produces normalized, cross-referenced, wiki-ready JSON files in `extracted/`. The output serves a **wiki site** (consumer = human readers via wiki templates). Coverage = all 50+ V2 game systems, nothing excluded.

---

## 2. Architecture

### 2.1 Directory Layout

```
darkanddarker-wiki/
├── pipeline/
│   ├── core/                        # Shared library (NEW)
│   │   ├── __init__.py
│   │   ├── reader.py                # Raw JSON loading and glob helpers
│   │   ├── normalizer.py            # UE5 → clean Python dict
│   │   ├── resolver.py              # Cross-domain ID resolution
│   │   ├── writer.py                # Standardized output writers
│   │   └── analyzer.py             # Derived fields and analysis note helpers
│   │
│   ├── domains/                     # One package per domain (NEW)
│   │   ├── engine/
│   │   ├── items/
│   │   ├── classes/
│   │   ├── combat/
│   │   ├── spells/
│   │   ├── status/
│   │   ├── monsters/
│   │   ├── dungeons/
│   │   ├── spawns/
│   │   ├── economy/
│   │   ├── quests/
│   │   └── cosmetics/
│   │
│   ├── extract_all.py               # Phase orchestrator — REWRITTEN (see §6)
│   ├── extract_enums.py             # KEPT as-is (standalone, pre-spec, produces engine/enums.json)
│   └── utils.py                     # KEPT for backwards compat, re-exports core/ where possible
│
└── extracted/
    ├── engine/                      # enums.json already here (pre-spec output, kept as-is)
    ├── gameplay/                    # movement.json already here — pre-spec, manually authored,
    │                                #   does NOT conform to §5 format; kept as reference artifact
    ├── items/
    ├── classes/
    ├── combat/
    ├── spells/
    ├── status/
    ├── monsters/
    ├── dungeons/
    ├── spawns/
    ├── economy/
    ├── quests/
    └── cosmetics/
```

**Migration notes for existing files:**
- `pipeline/extract_enums.py` — kept unchanged. It is standalone and already produces `extracted/engine/enums.json` in a compatible format (with the `displayName` key used by the resolver — see §5.4).
- `pipeline/extract_*.py` (7 domain stubs) — replaced by `pipeline/domains/<domain>/`. The old stubs are deleted during Phase 1 implementation.
- `pipeline/utils.py` — kept as a thin shim re-exporting `core/` helpers for any script still referencing it.
- `extracted/gameplay/movement.json` — pre-spec manually authored file. It does NOT conform to the §5 output format (uses camelCase keys, `_meta.extractedFrom`, `_meta.notes`). It is kept as a research/reference artifact and will be superseded by `extracted/combat/movement.json` produced by the `combat` domain extractor.
- `extracted/engine/enums.json` — pre-spec output but format is compatible. Kept and used by the resolver.

Each domain package exposes a single `run()` function called by `extract_all.py`. Inside each domain, each V2 system is a separate `extract_<system>.py` module.

---

## 3. Domain → V2 System Mapping

V2 (`raw/.../Data/Generated/V2/`) is the authoritative source. Legacy `DT_*` variants are fallback only when a V2 entry is absent.

| Domain | V2 Systems Owned |
|---|---|
| `engine` | Constant, IdTagGroup, AbilityRelationshipTagGroup, GameplayCueTagGroup, GameplayEffectRelationTagGroup, TagMessageRelationshipTagGroup, InteractSettingGroup, UserDefinedEnum (raw/), **CT_ curve tables** (raw/.../GameplayAbility/), **CurveFloat** assets |
| `items` | Item, ItemProperty |
| `classes` | PlayerCharacter, Perk, Skill, ShapeShift |
| `combat` | MeleeAttack, Projectile, Aoe, MovementModifier, GEModifier |
| `spells` | Spell, Religion, FaustianBargain |
| `status` | ActorStatus, ActorStatusInWater, ActorStatusItemCosmetic, ActorStatusMonster |
| `monsters` | Monster |
| `dungeons` | Dungeon, FloorRule, Props, MapIcon, Vehicle |
| `spawns` | Spawner, LootDrop |
| `economy` | Merchant, Shop, Marketplace, Parcel, Workshop |
| `quests` | Quest, Achievement, TriumphLevel, Leaderboard, Announce |
| `cosmetics` | ActionSkin, ArmorSkin, CharacterSkin, ItemSkin, LobbySkin, LobbyEmote, Emote, NameplateSkin, Title, DlcPack, TrustedAccount, Music, Chat |

**Cross-linking notes:**
- `LootDrop` lives in `spawns/` but is linked into item entity files (item shows where it drops from)
- `FaustianBargain` lives in `spells/` but is cross-linked into monster entries
- `ActorStatusItemCosmetic` stays in `status/` (gameplay-relevant visual states, not pure cosmetics)
- `Religion` lives in `spells/` (it is a spell-category system)
- `CT_` curve tables (e.g., `CT_ActionSpeed.json`, `CT_Agility.json`, `CT_Strength.json`) define per-attribute stat-to-effect scaling and are reference data, assigned to `engine`

### 3.1 V2 Sub-Directory Exceptions

Three V2 top-level directories have internal layouts that do NOT follow the standard `V2/<System>/<System>/*.json` pattern. Extractors must use these actual subdirectory names:

| V2 Top-Level | Expected subdirs (wrong) | Actual subdirs (correct) |
|---|---|---|
| `V2/FloorRule/` | `FloorRule/` | `FloorPortal/`, `FloorRuleBlizzard/`, `FloorRuleDeathSwarm/`, ... |
| `V2/TrustedAccount/` | `TrustedAccount/` | `EnforcerRating/`, `TABadge/` |
| `V2/Shop/` | `Shop/` | `ShopActionSkin/`, `ShopArmorSkin/`, `ShopCharacterSkin/`, `ShopEmote/`, `ShopItemBundle/`, `ShopItemSkin/`, `ShopLobbyEmote/`, `ShopLobbySkin/`, `ShopNameplateSkin/`, `ShopRedstoneShard/` |

---

## 4. Core Library

### 4.1 `core/reader.py`
```
load(path)           → parse one raw JSON file → list[dict]
glob(pattern)        → find all matching raw files (returns sorted Path list)
find_by_type(type)   → scan raw/ for all files where obj["Type"] == type
get_properties(obj)  → safely extract obj["Properties"]
get_item(obj)        → safely extract obj["Properties"]["Item"] (V2 assets)
```

### 4.2 `core/normalizer.py`
```
flatten(value)       → recursively resolve UE5 nested structs
resolve_ref(value)   → { ObjectName, ObjectPath } → asset_id string
resolve_tag(value)   → { TagName: "X.Y.Z" } → "X.Y.Z"
resolve_text(value)  → { LocalizedString: "..." } → display string
camel_to_snake(key)  → "MoveSpeedBase" → "move_speed_base"
clean_flags(flags)   → "RF_Public | RF_Standalone | ..." → ["Public", "Standalone"]
```

### 4.3 `core/resolver.py`
Cross-domain ID linker. Built progressively as domains complete.
```
register(domain, id, record)  → adds to in-memory registry (orchestrator only — see thread note)
resolve(asset_path) → dict    → lookup by asset path or asset name
resolve_enum(name, index)     → display name from enums.json
load_domain(domain)           → hydrate registry from extracted/<domain>/
```

**Thread safety contract:** `register()` is called exclusively from the phase orchestrator (`extract_all.py`) after each domain completes, never from worker threads. Worker threads may call `resolve()` and `load_domain()` concurrently (read-only operations, safe). The implementation must protect the registry `dict` with a `threading.Lock` for any concurrent access pattern.

Extractors call `resolver.load_domain("engine")` before resolving enum labels, and `resolver.load_domain("items")` before resolving item references in loot tables.

### 4.4 `core/writer.py`
```
write_entity(domain, id, data)   → extracted/<domain>/<id>.json
write_index(domain, entries)     → extracted/<domain>/_index.json
write_system(domain, name, data) → extracted/<domain>/<name>.json
```
Every file receives `_meta: { extracted_at, source_files[], pipeline_version }`.

The canonical `_meta` source key is `source_files` (array of strings). This supersedes the `source` (singular) key in the existing `utils.py` and the `extractedFrom` key in the pre-spec `movement.json`. Pre-spec files are not retroactively updated.

### 4.5 `core/analyzer.py`
```
dps(damage, speed)                  → float
drop_rate_pct(weight, total)        → float
speed_at_base(multiplier, base=300) → float
add_notes(data, notes)              → injects "_analysis_notes" list
add_formula(data, name, expr, conf, caveats) → injects into "_formulas" list
```

---

## 5. Output File Format

### 5.1 Entity File — `extracted/<domain>/<id>.json`
```json
{
  "id": "longsword",
  "name": "Longsword",
  "type": "weapon",

  "damage": { "min": 32, "max": 47, "type": "physical" },
  "speed": 0.9,

  "dropped_by": ["skeleton_fighter"],
  "sold_by": ["weaponsmith"],

  "_derived": {
    "dps_min": 28.8,
    "dps_max": 42.3
  },

  "_analysis_notes": ["..."],

  "_meta": {
    "extracted_at": "2026-03-12T...",
    "source_files": ["raw/.../Id_Item_Longsword.json"],
    "pipeline_version": "1.0.0"
  }
}
```

### 5.2 Domain Index — `extracted/<domain>/_index.json`
```json
{
  "count": 147,
  "entries": [
    { "id": "longsword", "name": "Longsword", "type": "weapon", "subtype": "sword" }
  ],
  "_meta": { ... }
}
```

### 5.3 System File — `extracted/<domain>/<system>.json`
For non-entity systems (formulas, mechanic tables). Includes `_formulas` and `_analysis_notes` at top level.

Note: `extracted/gameplay/movement.json` is a pre-spec manually authored file that does not conform to this format. It is kept as a reference artifact. The canonical movement system output is `extracted/combat/movement.json` produced by the `combat` domain.

### 5.4 Format Rules
- All keys: `snake_case`
- All asset path references resolved to human-readable IDs — never raw UE5 paths
- Enum values use the key `displayName` (matching existing `enums.json` output): `{ "index": 2, "name": "NewEnumerator2", "displayName": "Lessthan" }`
- `_derived`, `_analysis_notes`, `_formulas`, `_meta` always last in the object
- Durations: `duration_ms`; speeds: `speed_units`; costs: `cost_gold`
- `_meta.source_files` is always an array, even when there is only one source file

---

## 6. Execution Order & Dependency Graph

```
Phase 1 (sequential)  engine
Phase 2 (parallel)    items | classes | monsters
Phase 3 (parallel)    combat | spells | status
Phase 4 (parallel)    dungeons | spawns
                        ↑ spawns is Phase 4 (not Phase 3) because LootDrop files contain
                          ItemId asset path references requiring items to be in the resolver.
                          dungeons has no item refs and is safe to co-run with spawns.
Phase 5 (sequential)  economy
Phase 6 (parallel)    quests | cosmetics
```

### `extract_all.py` structure (rewritten)
```python
PHASES = [
    ["engine"],
    ["items", "classes", "monsters"],
    ["combat", "spells", "status"],
    ["dungeons", "spawns"],   # spawns needs items in resolver; dungeons is ref-independent
    ["economy"],
    ["quests", "cosmetics"],
]
```

Domains within a phase run via `concurrent.futures.ThreadPoolExecutor`. The orchestrator calls `resolver.register()` after each domain completes (not from worker threads — see §4.3 thread safety contract).

**Failure handling:**
- Phase failure → downstream phases skipped, not run with incomplete data
- Run summary printed at end: per-domain status + output file counts

**CLI flags:**
- `extract_all.py --domain items` — re-run items + downstream only
- `extract_all.py --force` — re-run all regardless of timestamps
- Default: skip domain if source files unchanged since last run (manifest timestamps)

---

## 7. Analysis Notes System

Three tiers of intelligence per output file:

### Tier 1 — Derived fields (`_derived`)
Auto-computed from raw numbers. Always present for entity files.
Examples: `dps_min`, `dps_max`, `drop_rate_pct`, `effective_speed_at_base`

### Tier 2 — Formula documentation (`_formulas`)
```json
{
  "name": "final_damage",
  "expression": "(base_damage + str_bonus) * (1 - armor_reduction)",
  "confidence": "medium",
  "caveats": ["armor_reduction coefficient is in C++ AttributeSet, not data assets"]
}
```

**Confidence levels:**

| Level | Meaning |
|---|---|
| `confirmed` | Value read directly from data asset |
| `computed` | Derived from confirmed values via known formula |
| `inferred` | Pattern-matched from multiple data points; formula in blueprint |
| `unknown` | Observed in data but semantics unclear |

### Tier 3 — Analysis notes (`_analysis_notes`)
Plain English. Wiki-ready. Explain mechanics, cross-system interactions, player implications.

**Coverage:**
- System files → full Tier 1 + 2 + 3
- Entity files → Tier 1 always; Tier 3 when meaningful (not boilerplate)
- Index files → no analysis (pure lookup)

---

## 8. Open Questions / Future Adjustments

- Domain assignments may shift as new systems are discovered during implementation
- Some V2 systems may contain sub-systems not yet visible from directory listing alone (see §3.1 for known exceptions)
- Blueprint-level formulas (C++ AttributeSet logic) can only be inferred, not read directly — confidence flags handle this
- New domains may be added if a discovered system doesn't fit existing groupings
- CT_ curve table format (Time/Value pairs) will require dedicated parsing logic in the engine extractor

---

## 9. Implementation Order

1. **Phase 1:** `core/` library + `engine/` domain — delete old domain stubs, set up `domains/` structure
2. **Phase 2:** `items/`, `classes/`, `monsters/` domains in parallel
3. **Phase 3:** `combat/`, `spells/`, `status/` domains in parallel
4. **Phase 4:** `dungeons/`, `spawns/` domains in parallel
5. **Phase 5:** `economy/` domain
6. **Phase 6:** `quests/`, `cosmetics/` domains in parallel
7. **Final:** Rewrite `extract_all.py` with phase orchestrator, CLI flags, and parallel execution
