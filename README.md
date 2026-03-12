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

## License

MIT
