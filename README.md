# Dark and Darker Wiki

Community-driven wiki built from game data extracted via [FModel](https://fmodel.app/). Includes a data extraction pipeline, a Next.js wiki website, and standalone calculator tools.

## Repository Structure

```
darkanddarker-wiki/
  raw/           # FModel JSON exports (gitignored — see Setup)
  pipeline/      # Python scripts that parse raw → extracted
  extracted/     # Normalized JSON committed to git
    gameplay/    #   Status effects, damage formulas, mechanics
    items/       #   Weapons, armor, accessories, consumables
    maps/        #   Module layouts, extraction points, spawns
    monsters/    #   Mob stats, resistances, loot tables
    classes/     #   Class stats, perks, skills, spells
    economy/     #   Merchant prices, crafting recipes
    engine/      #   Internal IDs, enums, asset references
  website/       # Next.js 14 wiki app (App Router)
  tools/         # Standalone HTML/JS calculators
```

## Setup

### Prerequisites

- **Node.js** >= 18
- **Python** >= 3.10
- **FModel** (to generate raw exports — optional if you only work on the website)

### Quick Start

```bash
# Clone and install
git clone <repo-url> && cd darkanddarker-wiki
npm install

# Run the website locally
npm run dev

# Run the full extraction pipeline (requires raw/ data)
npm run pipeline
```

### Populating `raw/`

1. Open FModel and point it at your Dark and Darker installation
2. Export the game files as JSON to the `raw/` directory
3. The directory structure inside `raw/` should mirror FModel's default export layout

> `raw/` is gitignored. You must generate these exports locally.

## Contributing

### Website (Next.js)

```bash
cd website
npm run dev        # Start dev server at http://localhost:3000
npm run build      # Production build
```

All wiki pages read from `extracted/` JSON at build time via server components. To add or edit a wiki page, you generally only need to touch files in `website/`.

### Pipeline (Python)

```bash
# Run a single domain extractor
npm run pipeline:items

# Run all extractors
npm run pipeline
```

Each script in `pipeline/` is independent — see [pipeline/README.md](pipeline/README.md) for details on what each script does and how to add new extractors.

### Tools (HTML/JS)

Standalone pages in `tools/`. No build step — open the HTML file directly in a browser or serve with any static file server. Each tool is self-contained.

### Contribution Guidelines

1. **Branch from `main`** — use `feature/`, `fix/`, or `data/` prefixes
2. **Pipeline changes** — always re-run the affected extractor and commit updated `extracted/` JSON
3. **Website changes** — make sure `npm run build` passes before opening a PR
4. **Data accuracy** — if you spot incorrect game data, check whether the issue is in the pipeline script or the raw export. File an issue if unsure.
5. **No raw data in PRs** — never commit files from `raw/`. If a new export format is needed, document it in the PR description.

## Architecture

```
FModel → raw/ → pipeline/ → extracted/ → website/ (build time)
                                       → tools/   (runtime)
```

The pipeline transforms Unreal Engine DataTable and Blueprint JSON into clean, normalized schemas. The website reads these at build time (Next.js static generation), so the live site has zero runtime dependency on the pipeline.

## FModel Export Process

Game data lives in `raw/` (gitignored). This directory must be populated locally using FModel before running the pipeline.

### FModel Setup

- **FModel version:** 4.6+ recommended (must support UE5 .utoc/.ucas archives)
- **Game directory:** Point FModel at your Dark and Darker installation (e.g., `C:\Program Files\Steam\steamapps\common\Dark and Darker`)
- **Export format:** JSON (`Settings > Models > Export as JSON`)
- **Output directory:** Set FModel's output to `raw/` inside this repo

### Export Settings

1. Open FModel and load the game's `.utoc` archive
2. Navigate to `DungeonCrawler/Content/` in the asset browser
3. Right-click the `DungeonCrawler` folder and select **Export Folder**
4. Also export `Localization/Game/en/` for quest titles and UI strings
5. The resulting directory structure should be:
   ```
   raw/
     DungeonCrawler/
       Content/
         DungeonCrawler/
           Data/Generated/V2/   # Items, spawners, loot tables, quests
           Maps/Dungeon/Modules/ # Module layouts per dungeon
         Localization/
           Game/en/Game.json    # English localization strings
   ```

### Refreshing After a Game Update

1. Open FModel and let it detect the updated archives
2. Re-export the `DungeonCrawler/Content/` tree to `raw/`
3. Run the build pipeline: `bash scripts/build.sh --all`
4. Verify extracted data: `bash scripts/build.sh --validate`

> FModel exports are deterministic for the same game version. Two people exporting the same patch will get identical JSON output.

## License

MIT
