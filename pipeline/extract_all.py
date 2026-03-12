"""Run all extraction scripts in dependency order."""

import subprocess
import sys
from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parent

# Ordered by dependency: engine first (reference data), then items, classes, etc.
SCRIPTS = [
    "extract_engine.py",
    "extract_items.py",
    "extract_classes.py",
    "extract_monsters.py",
    "extract_gameplay.py",
    "extract_economy.py",
    "extract_maps.py",
]


def main():
    failed = []
    for script in SCRIPTS:
        path = PIPELINE_DIR / script
        if not path.exists():
            print(f"[SKIP] {script} — not yet implemented")
            continue

        print(f"\n[RUN] {script}")
        result = subprocess.run([sys.executable, str(path)], cwd=str(PIPELINE_DIR))
        if result.returncode != 0:
            print(f"[FAIL] {script} exited with code {result.returncode}")
            failed.append(script)
        else:
            print(f"[OK]   {script}")

    if failed:
        print(f"\n{len(failed)} script(s) failed: {', '.join(failed)}")
        sys.exit(1)
    else:
        print("\nAll extraction scripts completed successfully.")


if __name__ == "__main__":
    main()
