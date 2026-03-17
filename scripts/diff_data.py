"""Compare two directories of JSON data files and produce a human-readable changelog.

Usage:
    py diff_data.py old_dir/ new_dir/ [--output docs/changelogs/]
"""
import argparse
import json
import difflib
from pathlib import Path
from datetime import date


def normalize_json(filepath: Path) -> str:
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False)


def diff_file(old_path: Path, new_path: Path) -> list[str]:
    old_lines = normalize_json(old_path).splitlines(keepends=True)
    new_lines = normalize_json(new_path).splitlines(keepends=True)
    return list(difflib.unified_diff(
        old_lines, new_lines,
        fromfile=str(old_path), tofile=str(new_path),
    ))


def main():
    parser = argparse.ArgumentParser(description="Diff JSON data directories")
    parser.add_argument("old_dir", type=Path)
    parser.add_argument("new_dir", type=Path)
    parser.add_argument("--output", type=Path, default=Path("docs/changelogs"))
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    out_file = args.output / f"{date.today().isoformat()}.diff"

    all_diffs: list[str] = []
    json_files = sorted(args.new_dir.glob("*.json"))

    for new_file in json_files:
        old_file = args.old_dir / new_file.name
        if old_file.exists():
            diff = diff_file(old_file, new_file)
            if diff:
                all_diffs.extend(diff)
                print(f"  Changed: {new_file.name} ({len(diff)} diff lines)")
            else:
                print(f"  Unchanged: {new_file.name}")
        else:
            print(f"  New: {new_file.name}")
            all_diffs.append(f"--- /dev/null\n+++ {new_file}\n(new file)\n")

    for old_file in sorted(args.old_dir.glob("*.json")):
        if not (args.new_dir / old_file.name).exists():
            print(f"  Deleted: {old_file.name}")
            all_diffs.append(f"--- {old_file}\n+++ /dev/null\n(deleted)\n")

    with open(out_file, "w", encoding="utf-8") as f:
        f.writelines(all_diffs)

    print(f"\nChangelog written to {out_file} ({len(all_diffs)} lines)")


if __name__ == "__main__":
    main()
