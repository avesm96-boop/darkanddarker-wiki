# Monster Extended Data — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add combo chains, status effects (with icons), loot drops, hunting loot, projectiles, AoE, and per-grade abilities to every monster page.

**Architecture:** Extend `build_monsters.py` with new extraction functions that read from raw UE4 JSON files and produce additional fields in `monsters.json`. Copy status effect icon PNGs to the public directory. Add new UI sections to `MonsterDetail.tsx` that render the extended data.

**Tech Stack:** Python (data pipeline), React/Next.js (frontend), status effect PNGs (70x70 icons)

**Deferred:** AI behavior extraction is omitted from this iteration. Behavior trees contain 100+ nodes with complex decision logic that doesn't reduce to a simple structured format. Can be revisited later with a summarization approach.

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `tools/build_monsters.py` | Modify | Add 6 new extraction functions + icon copy step |
| `website/public/data/monsters.json` | Auto-generated | Extended schema with new fields |
| `website/src/app/monsters/[slug]/MonsterDetail.tsx` | Modify | Add types + 5 new UI sections |
| `website/public/icons/status/*.png` | Copy (build step) | Status effect icons served statically |

---

## Chunk 1: Backend Data Extraction

### Task 1: Add combo chain extraction to build_monsters.py

Combo chains are encoded in the Abilities array. Entries with `_From_` in the name represent transitions: `Id_MonsterAbility_{Monster}_{Attack}_From_{Source}` means "from Source → Attack". Also entries prefixed `Combo_` like `Combo_WaterArrow_1_From_TailSlash_High`.

**Files:**
- Modify: `tools/build_monsters.py`

- [ ] **Step 1: Add `extract_combos()` function**

After the existing `process_ability()` function (~line 227), add:

```python
def extract_combos(abilities: list[str], monster_base: str) -> list[dict]:
    """Extract combo chain transitions from ability names.

    Abilities with '_From_' encode transitions: the part before '_From_' is the
    destination attack, the part after is the source. Returns a deduplicated list.
    """
    combos = []
    seen = set()
    for ability_ref in abilities:
        name = extract_asset_name(ability_ref)
        # Strip prefix
        if name.startswith("Id_MonsterAbility_"):
            name = name[len("Id_MonsterAbility_"):]
        # Strip monster base name
        if name.startswith(monster_base + "_"):
            name = name[len(monster_base) + 1:]
        # Strip "Combo_" prefix if present
        if name.startswith("Combo_"):
            name = name[len("Combo_"):]

        if "_From_" not in name:
            continue

        parts = name.split("_From_", 1)
        if len(parts) != 2:
            continue

        to_attack = parts[0].replace("_", " ").strip()
        from_attack = parts[1].replace("_", " ").strip()

        key = (from_attack, to_attack)
        if key not in seen:
            seen.add(key)
            combos.append({"from": from_attack, "to": to_attack})

    return combos
```

- [ ] **Step 2: Wire combo extraction into the main loop**

In `main()`, inside the `for variant in variants:` loop (after the abilities processing ~line 425-429), add combo extraction. The combos should be collected per-grade since abilities differ between Common/Elite.

In the grade processing block, after processing abilities, add:

```python
                # Extract combo chains from this grade's abilities
                ability_paths = [a.get("AssetPathName", "") for a in props.get("Abilities", [])]
                grade_combos = extract_combos(ability_paths, base_name)
```

Then store combos per grade in the `grades[grade_str]` dict:

```python
            grades[grade_str] = {
                "adv_point": variant.get("adv_point", 0),
                "exp_point": variant.get("exp_point", 0),
                "stats": stats,
                "abilities_list": [clean_attack_name(extract_asset_name(a.get("AssetPathName", "")), base_name)
                                   for a in props.get("Abilities", [])
                                   if not should_skip_ability(extract_asset_name(a.get("AssetPathName", ""))[len("Id_MonsterAbility_"):] if extract_asset_name(a.get("AssetPathName", "")).startswith("Id_MonsterAbility_") else extract_asset_name(a.get("AssetPathName", "")))],
                "combos": grade_combos,
            }
```

- [ ] **Step 3: Run build_monsters.py and verify combos appear in output**

Run: `python tools/build_monsters.py`

Then check the Ancient Stingray entry in `website/public/data/monsters.json` for `combos` in each grade.

- [ ] **Step 4: Commit**

```bash
git add tools/build_monsters.py
git commit -m "feat(monsters): extract combo chains from ability data"
```

---

### Task 2: Add status effects extraction + icon copying

Status effects live in `raw/.../ActorStatus/Debuff/Monster/{ImageFolder}/`. Each `GE_*.json` file is a gameplay effect. The UIData object inside references an icon texture name. Icons are PNGs at `raw/.../UI/Resources/IconActorStatus/`.

**Files:**
- Modify: `tools/build_monsters.py`

- [ ] **Step 1: Add directory constants**

At the top of `build_monsters.py`, after the existing constants (~line 23), add:

```python
RAW_STATUS_BASE = ROOT / "raw" / "DungeonCrawler" / "Content" / "DungeonCrawler" / "ActorStatus" / "Debuff" / "Monster"
RAW_ICON_DIR = ROOT / "raw" / "DungeonCrawler" / "Content" / "DungeonCrawler" / "UI" / "Resources" / "IconActorStatus"
STATUS_ICON_OUT = ROOT / "website" / "public" / "icons" / "status"
```

- [ ] **Step 2: Add `extract_status_effects()` function**

```python
def extract_status_effects(image_folder: str) -> tuple[list[dict], set[str]]:
    """Extract status effects from ActorStatus/Debuff/Monster/{folder}/.

    Returns (effects_list, set_of_icon_names_to_copy).
    """
    status_dir = RAW_STATUS_BASE / image_folder
    if not status_dir.exists():
        return [], set()

    effects = []
    icons_needed = set()

    for ge_file in sorted(status_dir.glob("GE_*.json")):
        data = load_json(ge_file)
        if not data:
            continue

        effect_name = ge_file.stem  # e.g. GE_AncientStingray_TailPoison
        # Clean the name: strip GE_ prefix and monster name
        clean_name = effect_name
        if clean_name.startswith("GE_"):
            clean_name = clean_name[3:]
        # Strip image_folder prefix (monster name)
        if clean_name.startswith(image_folder + "_"):
            clean_name = clean_name[len(image_folder) + 1:]
        clean_name = clean_name.replace("_", " ")

        # Find icon from UIData reference
        icon_name = ""
        tags = []
        for obj in data if isinstance(data, list) else [data]:
            obj_type = obj.get("Type", "")
            props = obj.get("Properties", {})

            # DCGameplayEffectUIData contains the icon reference
            if obj_type == "DCGameplayEffectUIData":
                ui_asset = props.get("UIDataAsset", {})
                ui_path = ui_asset.get("ObjectPath", "")
                if ui_path:
                    # Read the UIData file to get icon texture name
                    # Path: same directory as the GE_ file
                    ui_name = ui_asset.get("ObjectName", "").split("'")[-2] if "'" in ui_asset.get("ObjectName", "") else ""
                    if ui_name:
                        ui_file = status_dir / f"{ui_name}.json"
                        ui_data = load_json(ui_file)
                        if ui_data:
                            for ui_obj in ui_data if isinstance(ui_data, list) else [ui_data]:
                                icon_tex = ui_obj.get("Properties", {}).get("IconTexture", {})
                                tex_name = icon_tex.get("ObjectName", "")
                                if "'" in tex_name:
                                    icon_name = tex_name.split("'")[-2]
                                    icons_needed.add(icon_name)

            # Extract gameplay tags from the main GE_ object
            if obj_type.startswith("GE_") or (obj_type == effect_name + "_C"):
                removal_tags = props.get("RemovalTagRequirements", {}).get("RequireTags", [])
                for tag in removal_tags:
                    # Extract the last meaningful segment
                    parts = tag.split(".")
                    if len(parts) >= 3:
                        tags.append(parts[-1])

        effects.append({
            "name": clean_name,
            "icon": icon_name,
            "tags": tags,
        })

    return effects, icons_needed
```

- [ ] **Step 3: Add icon copy step**

After the main processing loop, add an icon copy step:

```python
def copy_status_icons(icons_needed: set[str]):
    """Copy referenced status effect icon PNGs to the public directory."""
    if not icons_needed:
        return
    import shutil  # Note: move to module-level imports when implementing
    STATUS_ICON_OUT.mkdir(parents=True, exist_ok=True)
    copied = 0
    for icon_name in sorted(icons_needed):
        src = RAW_ICON_DIR / f"{icon_name}.png"
        dst = STATUS_ICON_OUT / f"{icon_name}.png"
        if src.exists():
            shutil.copy2(src, dst)
            copied += 1
    print(f"  Copied {copied}/{len(icons_needed)} status effect icons")
```

- [ ] **Step 4: Wire status effects into the main loop**

In `main()`, before the per-monster loop, initialize an icon set:

```python
    all_icons_needed: set[str] = set()
```

Inside the per-monster processing (after finding `image_folder`), add:

```python
        # Extract status effects
        status_effects, icons = extract_status_effects(image_folder)
        all_icons_needed.update(icons)
```

Add `"status_effects": status_effects` to the monster output dict.

After the main loop (before writing JSON), add:

```python
    # Copy status effect icons
    copy_status_icons(all_icons_needed)
```

- [ ] **Step 5: Run and verify**

Run: `python tools/build_monsters.py`

Verify:
- `monsters.json` has `status_effects` with icon names
- `website/public/icons/status/` contains PNG files

- [ ] **Step 6: Commit**

```bash
git add tools/build_monsters.py website/public/icons/status/
git commit -m "feat(monsters): extract status effects with icon pipeline"
```

---

### Task 3: Add loot drops extraction

Loot data lives in `raw/.../V2/LootDrop/LootDropGroup/ID_LootdropGroup_{BaseName}.json`. Each entry has a `LootDropId` reference (e.g., `ID_Lootdrop_Drop_AncientStingray`), a `LootDropRateId`, and `LootDropCount`. We extract the unique drop types and quantities from dungeon grade 0 (the base drops).

**Files:**
- Modify: `tools/build_monsters.py`

- [ ] **Step 1: Add loot directory constant**

```python
RAW_LOOTDROP_DIR = ROOT / "raw" / "DungeonCrawler" / "Content" / "DungeonCrawler" / "Data" / "Generated" / "V2" / "LootDrop"
```

- [ ] **Step 2: Add `extract_loot_drops()` function**

```python
def extract_loot_drops(base_name: str) -> list[dict]:
    """Extract loot drop info from LootDropGroup files.

    Reads DungeonGrade=0 entries (base drops shared across all dungeon grades).
    """
    group_file = RAW_LOOTDROP_DIR / "LootDropGroup" / f"ID_LootdropGroup_{base_name}.json"
    data = load_json(group_file)
    if not data:
        return []

    props = data[0].get("Properties", {}) if isinstance(data, list) else data.get("Properties", {})
    items = props.get("LootDropGroupItemArray", [])

    drops = []
    seen = set()
    for item in items:
        if item.get("DungeonGrade", -1) != 0:
            continue
        drop_path = item.get("LootDropId", {}).get("AssetPathName", "")
        drop_name = extract_asset_name(drop_path)
        count = item.get("LootDropCount", 1)

        if not drop_name or drop_name in seen or count <= 0:
            continue
        seen.add(drop_name)

        # Clean name: strip ID_Lootdrop_Drop_ or ID_Lootdrop_Spawn_ prefix
        clean = drop_name
        for prefix in ["ID_Lootdrop_Drop_", "ID_Lootdrop_Spawn_"]:
            if clean.startswith(prefix):
                clean = clean[len(prefix):]
        clean = re.sub(r"([a-z])([A-Z])", r"\1 \2", clean)

        drops.append({"name": clean, "quantity": count})

    return drops
```

- [ ] **Step 3: Wire into main loop and output**

Inside per-monster processing:

```python
        loot_drops = extract_loot_drops(base_name)
```

Add `"loot": loot_drops` to the monster output dict.

- [ ] **Step 4: Run and verify**

Run: `python tools/build_monsters.py`

Check that Ancient Stingray has 3 loot entries (AncientStingray x3, CorrodedKey x1, EventCurrency x1).

- [ ] **Step 5: Commit**

```bash
git add tools/build_monsters.py
git commit -m "feat(monsters): extract loot drop data"
```

---

### Task 4: Add hunting loot extraction

Hunting loot items have `MiscType.TagName == "Type.Item.Misc.HuntingLoot"` in their extracted JSON. Cross-reference by checking if the item name contains the monster base name.

**Files:**
- Modify: `tools/build_monsters.py`

- [ ] **Step 1: Add raw items directory constant**

```python
RAW_ITEM_DIR = ROOT / "raw" / "DungeonCrawler" / "Content" / "DungeonCrawler" / "Data" / "Generated" / "V2" / "Item" / "Item"
```

- [ ] **Step 2: Add `build_hunting_loot_map()` function**

This builds a lookup from monster base name → hunting loot data, called once before the main loop.
Must read from raw V2 item files (not extracted/) because the `MiscType` HuntingLoot tag
only exists in the raw UE4 JSON format.

```python
def build_hunting_loot_map() -> dict[str, dict]:
    """Build a map of monster base name (lowercase) -> hunting loot item data.

    Scans raw V2 item files for MiscType == Type.Item.Misc.HuntingLoot.
    """
    result = {}
    if not RAW_ITEM_DIR.exists():
        return result

    for item_file in RAW_ITEM_DIR.glob("Id_Item_*.json"):
        data = load_json(item_file)
        if not data:
            continue

        # Raw V2 items are arrays of UE4 objects
        props = data[0].get("Properties", {}) if isinstance(data, list) else data.get("Properties", {})
        misc_type = props.get("MiscType", {})
        tag_name = misc_type.get("TagName", "") if isinstance(misc_type, dict) else str(misc_type)
        if "HuntingLoot" not in tag_name:
            continue

        item_id = item_file.stem  # e.g. Id_Item_AncientStingrayEgg
        # Get localized name and flavor text
        name_obj = props.get("Name", {})
        item_name = name_obj.get("LocalizedString", "") if isinstance(name_obj, dict) else str(name_obj)
        flavor_obj = props.get("FlavorText", {})
        flavor = flavor_obj.get("LocalizedString", "") if isinstance(flavor_obj, dict) else str(flavor_obj)
        rarity_obj = props.get("RarityType", {})
        rarity_tag = rarity_obj.get("TagName", "") if isinstance(rarity_obj, dict) else str(rarity_obj)
        rarity = rarity_tag.rsplit(".", 1)[-1] if rarity_tag else ""

        # Derive monster name from item id: strip Id_Item_ prefix, then strip common suffixes
        base = item_id
        if base.startswith("Id_Item_"):
            base = base[len("Id_Item_"):]
        # Remove common hunting loot suffixes
        for suffix in ["Egg", "Fang", "Horn", "Claw", "Scale", "Eye", "Heart",
                        "Wing", "Tooth", "Bone", "Hide", "Pelt", "Tail", "Head",
                        "Skull", "Trophy", "Essence", "Core", "Gem", "Crystal",
                        "Feather", "Antenna", "Shell", "Husk", "Stinger",
                        "LootItem", "Loot"]:
            if base.endswith(suffix) and len(base) > len(suffix):
                base = base[:-len(suffix)]
                break

        result[base.lower()] = {
            "name": item_name,
            "rarity": rarity,
            "description": flavor,
        }

    return result
```

- [ ] **Step 3: Wire into main()**

Before the main monster loop:

```python
    hunting_loot_map = build_hunting_loot_map()
    print(f"  Found {len(hunting_loot_map)} hunting loot items")
```

Inside per-monster processing:

```python
        hunting_loot = hunting_loot_map.get(base_name.lower())
```

Add `"hunting_loot": hunting_loot` to the monster output dict (will be `null` if not found).

- [ ] **Step 4: Run and verify**

Run: `python tools/build_monsters.py`

Verify Ancient Stingray has `hunting_loot: { name: "Ancient Stingray Egg", rarity: "Epic", description: "An egg with..." }`.

- [ ] **Step 5: Commit**

```bash
git add tools/build_monsters.py
git commit -m "feat(monsters): extract hunting loot items"
```

---

### Task 5: Add projectiles and AoE extraction

Projectiles are identified from `Characters/Monster/{ImageFolder}/BP_{ImageFolder}_*.json` files that inherit from `BP_ProjectileActor`. AoE definitions are in `raw/.../V2/Aoe/Aoe/Id_Aoe_{BaseName}_*.json`.

**Files:**
- Modify: `tools/build_monsters.py`

- [ ] **Step 1: Add AoE directory constant**

Use `extracted/combat/` which has more complete AoE data (682 files vs 49 in raw).

```python
EXTRACTED_AOE_DIR = ROOT / "extracted" / "combat"
```

- [ ] **Step 2: Add `extract_projectiles()` function**

```python
def extract_projectiles(image_folder: str) -> list[dict]:
    """Extract projectile types from blueprint files.

    Scans BP_*.json files that inherit from BP_ProjectileActor.
    """
    monster_dir = CHARACTERS_DIR / image_folder
    if not monster_dir.exists():
        return []

    projectiles = []
    seen = set()
    for bp_file in sorted(monster_dir.glob("BP_*.json")):
        data = load_json(bp_file)
        if not data:
            continue

        # Check if any object inherits from BP_ProjectileActor
        is_projectile = False
        for obj in data if isinstance(data, list) else [data]:
            super_ref = obj.get("Super", {})
            super_name = super_ref.get("ObjectName", "")
            if "ProjectileActor" in super_name:
                is_projectile = True
                break

        if not is_projectile:
            continue

        name = bp_file.stem  # e.g. BP_AncientStingray_WaterArrow
        # Clean name
        clean = name
        if clean.startswith("BP_"):
            clean = clean[3:]
        if clean.startswith(image_folder + "_"):
            clean = clean[len(image_folder) + 1:]
        clean = clean.replace("_", " ")

        if clean not in seen:
            seen.add(clean)
            projectiles.append({"name": clean})

    return projectiles
```

- [ ] **Step 3: Add `extract_aoe()` function**

```python
def extract_aoe(base_name: str) -> list[dict]:
    """Extract AoE definitions from extracted combat data.

    Extracted AoE files have format: { "id": "Id_Aoe_...", "abilities": [...] }
    """
    if not EXTRACTED_AOE_DIR.exists():
        return []

    aoes = []
    for aoe_file in sorted(EXTRACTED_AOE_DIR.glob(f"Id_Aoe_{base_name}_*.json")):
        data = load_json(aoe_file)
        if not data:
            continue

        aoe_id = data.get("id", aoe_file.stem)
        # Clean name: strip Id_Aoe_ prefix and monster base name
        clean = aoe_id
        if clean.startswith("Id_Aoe_"):
            clean = clean[7:]
        if clean.startswith(base_name + "_"):
            clean = clean[len(base_name) + 1:]
        clean = clean.replace("_", " ")

        aoes.append({"name": clean})

    return aoes
```

- [ ] **Step 4: Wire into main loop**

Inside per-monster processing:

```python
        projectiles = extract_projectiles(image_folder)
        aoe = extract_aoe(base_name)
```

Add `"projectiles": projectiles` and `"aoe": aoe` to the monster output dict.

- [ ] **Step 5: Run and verify**

Run: `python tools/build_monsters.py`

Verify Ancient Stingray has projectiles (WaterArrow, Rock variants) and AoE (LightningBubble, LightningPoint).

- [ ] **Step 6: Commit**

```bash
git add tools/build_monsters.py
git commit -m "feat(monsters): extract projectiles and AoE data"
```

---

### Task 6: Add per-grade abilities list

The abilities list already exists in the pipeline but is merged across grades into a single `attacks` array. We need to also store the raw ability name list per grade so the frontend can show which abilities are exclusive to Elite/Nightmare.

**Files:**
- Modify: `tools/build_monsters.py`

- [ ] **Step 1: Clean the abilities_list in the grade dict**

The `abilities_list` was roughed in during Task 1. Simplify it to use a cleaner extraction:

```python
                # Build clean abilities list for this grade
                grade_abilities = []
                for ability_ref in props.get("Abilities", []):
                    aname = extract_asset_name(ability_ref.get("AssetPathName", ""))
                    check = aname[len("Id_MonsterAbility_"):] if aname.startswith("Id_MonsterAbility_") else aname
                    if not should_skip_ability(check):
                        grade_abilities.append(clean_attack_name(aname, base_name))
```

Store as `"abilities": grade_abilities` in the grade dict.

- [ ] **Step 2: Run and verify**

Run: `python tools/build_monsters.py`

Verify that Elite grade has `Rush FallingRock` and `LightningBubble Elite` in its abilities list while Common does not.

- [ ] **Step 3: Commit**

```bash
git add tools/build_monsters.py
git commit -m "feat(monsters): store per-grade abilities list"
```

---

## Chunk 2: Frontend UI Sections

### Task 7: Update TypeScript types in MonsterDetail.tsx

**Files:**
- Modify: `website/src/app/monsters/[slug]/MonsterDetail.tsx`

- [ ] **Step 1: Add new interfaces**

After the existing `Attack` interface (~line 23), add:

```typescript
interface Combo {
  from: string;
  to: string;
}

interface StatusEffect {
  name: string;
  icon: string;
  tags: string[];
}

interface LootDrop {
  name: string;
  quantity: number;
}

interface HuntingLoot {
  name: string;
  rarity: string;
  description: string;
}

interface Projectile {
  name: string;
}

interface AoeDef {
  name: string;
}
```

- [ ] **Step 2: Extend the `MonsterGrade` interface**

Add to `MonsterGrade`:

```typescript
interface MonsterGrade {
  adv_point: number;
  exp_point: number;
  stats: Record<string, number>;
  combos?: Combo[];
  abilities?: string[];
}
```

- [ ] **Step 3: Extend the `Monster` interface**

Add to `Monster`:

```typescript
interface Monster {
  slug: string;
  name: string;
  class_type: string;
  creature_types: string[];
  image: string;
  dungeons: string[];
  grades: Record<string, MonsterGrade>;
  attacks: Attack[];
  status_effects?: StatusEffect[];
  loot?: LootDrop[];
  hunting_loot?: HuntingLoot;
  projectiles?: Projectile[];
  aoe?: AoeDef[];
}
```

- [ ] **Step 4: Commit**

```bash
git add website/src/app/monsters/[slug]/MonsterDetail.tsx
git commit -m "feat(monsters): add TypeScript types for extended data"
```

---

### Task 8: Add Status Effects UI section

Shows a grid of effect cards with icon (70x70), name, and tags. Placed after the Attacks section.

**Files:**
- Modify: `website/src/app/monsters/[slug]/MonsterDetail.tsx`

- [ ] **Step 1: Add StatusEffects section component**

After the `cleanAttackName` helper at the bottom of the file, add:

```typescript
function StatusEffectsSection({ effects }: { effects: StatusEffect[] }) {
  if (!effects.length) return null;
  return (
    <section style={{ marginBottom: "36px" }}>
      <SectionTitle>Status Effects ({effects.length})</SectionTitle>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: "8px" }}>
        {effects.map((eff, i) => (
          <div key={i} style={{
            display: "flex", alignItems: "center", gap: "10px",
            padding: "10px 14px", background: "var(--bg-card)",
            border: "1px solid var(--border-dim)", borderRadius: "2px",
          }}>
            {eff.icon && (
              <img
                src={`/icons/status/${eff.icon}.png`}
                alt={eff.name}
                width={36} height={36}
                style={{ imageRendering: "pixelated", flexShrink: 0 }}
              />
            )}
            <div>
              <div style={{ fontSize: "0.8125rem", color: "var(--text-bright)", fontWeight: 500 }}>
                {eff.name}
              </div>
              {eff.tags.length > 0 && (
                <div style={{ display: "flex", gap: "4px", flexWrap: "wrap", marginTop: "3px" }}>
                  {eff.tags.map((tag) => (
                    <span key={tag} style={{
                      fontSize: "0.5625rem", padding: "1px 6px",
                      background: "rgba(201,168,76,0.08)", color: "var(--text-muted)",
                      border: "1px solid var(--border-dim)", borderRadius: "1px",
                      fontFamily: "var(--font-heading)", letterSpacing: "0.08em",
                      textTransform: "uppercase",
                    }}>
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Render in main component**

After the Attacks section closing `)}` (~line 297), add:

```tsx
        {/* Status Effects */}
        {monster.status_effects && monster.status_effects.length > 0 && (
          <StatusEffectsSection effects={monster.status_effects} />
        )}
```

- [ ] **Step 3: Verify in browser**

Run: `npm run dev` (from website/)

Navigate to a monster page with status effects (e.g., Ancient Stingray). Verify icons render at 36x36 with name and tags.

- [ ] **Step 4: Commit**

```bash
git add website/src/app/monsters/[slug]/MonsterDetail.tsx
git commit -m "feat(monsters): add status effects UI section with icons"
```

---

### Task 9: Add Combo Chains UI section

Shows a table of attack transitions for the currently selected grade. Combos are per-grade since abilities differ between Common/Elite.

**Files:**
- Modify: `website/src/app/monsters/[slug]/MonsterDetail.tsx`

- [ ] **Step 1: Add ComboChainsSection component**

```typescript
function ComboChainsSection({ combos }: { combos: Combo[] }) {
  if (!combos.length) return null;
  return (
    <section style={{ marginBottom: "36px" }}>
      <SectionTitle>Combo Chains ({combos.length})</SectionTitle>
      <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
        {combos.map((combo, i) => (
          <div key={i} style={{
            display: "grid", gridTemplateColumns: "1fr auto 1fr", gap: "12px",
            alignItems: "center", padding: "8px 14px",
            background: "var(--bg-card)", border: "1px solid var(--border-dim)", borderRadius: "2px",
          }}>
            <span style={{ fontSize: "0.8125rem", color: "var(--text-bright)" }}>
              {combo.from}
            </span>
            <span style={{ fontSize: "0.75rem", color: "var(--gold-700)", fontFamily: "var(--font-heading)" }}>
              →
            </span>
            <span style={{ fontSize: "0.8125rem", color: "var(--gold-400)", fontWeight: 500 }}>
              {combo.to}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Render in main component (grade-aware)**

After the Status Effects section, add:

```tsx
        {/* Combo Chains (per grade) */}
        {gradeData?.combos && gradeData.combos.length > 0 && (
          <ComboChainsSection combos={gradeData.combos} />
        )}
```

- [ ] **Step 3: Verify in browser**

Navigate to Ancient Stingray, switch between Common/Elite grades. Verify combo count changes (Elite should have more transitions due to extra abilities).

- [ ] **Step 4: Commit**

```bash
git add website/src/app/monsters/[slug]/MonsterDetail.tsx
git commit -m "feat(monsters): add combo chains UI section"
```

---

### Task 10: Add Loot Drops and Hunting Loot UI sections

**Files:**
- Modify: `website/src/app/monsters/[slug]/MonsterDetail.tsx`

- [ ] **Step 1: Add LootSection component**

```typescript
const RARITY_COLORS: Record<string, string> = {
  Common: "var(--rarity-common)",
  Uncommon: "#1eff00",
  Rare: "#0070dd",
  Epic: "var(--gold-500)",
  Legendary: "#ff8000",
  Unique: "#e6cc80",
};

function LootSection({ loot, huntingLoot }: { loot: LootDrop[]; huntingLoot?: HuntingLoot | null }) {
  if (!loot.length && !huntingLoot) return null;
  return (
    <section style={{ marginBottom: "36px" }}>
      <SectionTitle>Loot</SectionTitle>

      {/* Drop table */}
      {loot.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "4px", marginBottom: huntingLoot ? "16px" : "0" }}>
          {loot.map((drop, i) => (
            <div key={i} style={{
              display: "flex", justifyContent: "space-between", alignItems: "center",
              padding: "8px 14px", background: "var(--bg-card)",
              border: "1px solid var(--border-dim)", borderRadius: "2px",
            }}>
              <span style={{ fontSize: "0.8125rem", color: "var(--text-bright)" }}>{drop.name}</span>
              <span style={{
                fontSize: "0.6875rem", padding: "2px 8px",
                background: "rgba(201,168,76,0.1)", color: "var(--gold-400)",
                borderRadius: "1px", fontFamily: "var(--font-heading)",
                fontWeight: 600,
              }}>
                ×{drop.quantity}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Hunting loot */}
      {huntingLoot && (
        <div style={{
          padding: "14px 16px", background: "var(--bg-card)",
          border: `1px solid ${RARITY_COLORS[huntingLoot.rarity] ?? "var(--border-dim)"}`,
          borderRadius: "2px",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
            <span style={{
              fontSize: "0.5625rem", padding: "2px 8px",
              background: `color-mix(in srgb, ${RARITY_COLORS[huntingLoot.rarity] ?? "var(--text-dim)"} 15%, transparent)`,
              color: RARITY_COLORS[huntingLoot.rarity] ?? "var(--text-dim)",
              borderRadius: "1px", fontFamily: "var(--font-heading)",
              fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase",
            }}>
              {huntingLoot.rarity}
            </span>
            <span style={{
              fontSize: "0.5625rem", padding: "2px 8px",
              background: "rgba(201,168,76,0.06)", color: "var(--text-muted)",
              borderRadius: "1px", fontFamily: "var(--font-heading)",
              letterSpacing: "0.12em", textTransform: "uppercase",
            }}>
              Hunting Loot
            </span>
          </div>
          <div style={{ fontSize: "0.875rem", color: "var(--text-bright)", fontWeight: 600, marginBottom: "4px" }}>
            {huntingLoot.name}
          </div>
          {huntingLoot.description && (
            <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", fontStyle: "italic", lineHeight: 1.5 }}>
              {huntingLoot.description}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
```

- [ ] **Step 2: Render in main component**

After Combo Chains section:

```tsx
        {/* Loot */}
        {((monster.loot && monster.loot.length > 0) || monster.hunting_loot) && (
          <LootSection loot={monster.loot ?? []} huntingLoot={monster.hunting_loot} />
        )}
```

- [ ] **Step 3: Verify in browser**

Check Ancient Stingray page: should show 3 drops (Ancient Stingray ×3, Corroded Key ×1, Event Currency ×1) and the hunting loot card with Epic border.

- [ ] **Step 4: Commit**

```bash
git add website/src/app/monsters/[slug]/MonsterDetail.tsx
git commit -m "feat(monsters): add loot drops and hunting loot UI sections"
```

---

### Task 11: Add Projectiles & AoE UI section

Combined section showing projectile and AoE cards.

**Files:**
- Modify: `website/src/app/monsters/[slug]/MonsterDetail.tsx`

- [ ] **Step 1: Add ProjectilesAoeSection component**

```typescript
function ProjectilesAoeSection({ projectiles, aoe }: { projectiles: Projectile[]; aoe: AoeDef[] }) {
  if (!projectiles.length && !aoe.length) return null;
  return (
    <section style={{ marginBottom: "36px" }}>
      <SectionTitle>Projectiles & AoE</SectionTitle>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
        {projectiles.map((p, i) => (
          <div key={`p-${i}`} style={{
            padding: "7px 14px", background: "var(--bg-card)",
            border: "1px solid var(--border-dim)", borderRadius: "2px",
            display: "flex", alignItems: "center", gap: "8px",
          }}>
            <span style={{
              fontSize: "0.5625rem", padding: "1px 6px",
              background: "rgba(85,136,187,0.12)", color: "#5588bb",
              borderRadius: "1px", fontFamily: "var(--font-heading)",
              letterSpacing: "0.08em", textTransform: "uppercase", fontWeight: 600,
            }}>
              Projectile
            </span>
            <span style={{ fontSize: "0.8125rem", color: "var(--text-bright)" }}>{p.name}</span>
          </div>
        ))}
        {aoe.map((a, i) => (
          <div key={`a-${i}`} style={{
            padding: "7px 14px", background: "var(--bg-card)",
            border: "1px solid var(--border-dim)", borderRadius: "2px",
            display: "flex", alignItems: "center", gap: "8px",
          }}>
            <span style={{
              fontSize: "0.5625rem", padding: "1px 6px",
              background: "rgba(201,168,76,0.12)", color: "var(--gold-500)",
              borderRadius: "1px", fontFamily: "var(--font-heading)",
              letterSpacing: "0.08em", textTransform: "uppercase", fontWeight: 600,
            }}>
              AoE
            </span>
            <span style={{ fontSize: "0.8125rem", color: "var(--text-bright)" }}>{a.name}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Render in main component**

After the Loot section:

```tsx
        {/* Projectiles & AoE */}
        {((monster.projectiles && monster.projectiles.length > 0) || (monster.aoe && monster.aoe.length > 0)) && (
          <ProjectilesAoeSection projectiles={monster.projectiles ?? []} aoe={monster.aoe ?? []} />
        )}
```

- [ ] **Step 3: Add per-grade abilities display**

After the Projectiles & AoE section, show the full abilities list for the current grade if it differs between grades:

```tsx
        {/* Per-Grade Abilities */}
        {gradeData?.abilities && gradeData.abilities.length > 0 && availableGrades.length > 1 && (
          <section style={{ marginBottom: "36px" }}>
            <SectionTitle>Abilities — {grade} ({gradeData.abilities.length})</SectionTitle>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "5px" }}>
              {gradeData.abilities.map((ability, i) => {
                // Check if this ability is NOT present in every other grade
                const isExclusive = availableGrades
                  .filter((g) => g !== grade)
                  .every((g) => !monster.grades[g]?.abilities?.includes(ability));
                return (
                  <span key={i} style={{
                    padding: "5px 11px", fontSize: "0.75rem",
                    background: isExclusive ? "rgba(201,168,76,0.1)" : "var(--bg-card)",
                    color: isExclusive ? "var(--gold-400)" : "var(--text-bright)",
                    border: `1px solid ${isExclusive ? "rgba(201,168,76,0.3)" : "var(--border-dim)"}`,
                    borderRadius: "2px", fontWeight: isExclusive ? 600 : 400,
                  }}>
                    {cleanAttackName(ability)}
                  </span>
                );
              })}
            </div>
            {availableGrades.length > 1 && (
              <div style={{
                fontSize: "0.625rem", color: "var(--text-muted)", marginTop: "8px",
                fontStyle: "italic",
              }}>
                Highlighted abilities are unique to this grade
              </div>
            )}
          </section>
        )}
```

- [ ] **Step 4: Verify in browser**

Check Ancient Stingray: should show projectiles (Water Arrow, Rock), AoE (Lightning Bubble, Lightning Point), and abilities list with Rush FallingRock and Lightning Bubble Elite highlighted in Elite grade.

- [ ] **Step 5: Commit**

```bash
git add website/src/app/monsters/[slug]/MonsterDetail.tsx
git commit -m "feat(monsters): add projectiles, AoE, and per-grade abilities UI"
```

---

### Task 12: Final integration run

- [ ] **Step 1: Full rebuild**

```bash
cd tools && python build_monsters.py && cd ../website && npm run build
```

- [ ] **Step 2: Smoke test**

Start dev server, check 3-4 monster pages:
- Ancient Stingray (boss, all sections populated)
- A normal monster (should have fewer sections, graceful empty handling)
- A monster without status effects (sections should not render)

- [ ] **Step 3: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix(monsters): integration fixes for extended data"
```
