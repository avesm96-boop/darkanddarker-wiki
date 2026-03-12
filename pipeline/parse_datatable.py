#!/usr/bin/env python3
"""
Parse FModel DataTable JSON exports into clean normalized arrays.

Handles both dict and array formats, flattens nested UAsset structs,
resolves soft object references, and normalizes field types.

Usage:
  python parse_datatable.py input.json --type Items --output output.json
  python parse_datatable.py raw/**/*.json --type Monsters
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Any, Union, Dict, List, Set


class DataTableParser:
    """Parse FModel DataTable exports."""

    def __init__(self, type_category: str = ""):
        self.type_category = type_category
        self.unknown_types: Set[str] = set()

    def parse_file(self, filepath: str) -> List[Dict[str, Any]]:
        """Read and parse a JSON file, auto-detecting format."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        return self.parse(data)

    def parse(self, data: Any) -> List[Dict[str, Any]]:
        """Parse data in either array or dict format."""
        if isinstance(data, list):
            # Array format: [{ 'Name': '...', 'Properties': {...} }, ...]
            return [self._normalize_row(row) for row in data if isinstance(row, dict)]

        elif isinstance(data, dict):
            # Check for 'Rows' key (dict-of-rows format)
            if "Rows" in data and isinstance(data["Rows"], dict):
                rows = data["Rows"]
                return [
                    {**self._normalize_row(row), "row_name": name}
                    for name, row in rows.items()
                    if isinstance(row, dict)
                ]

            # Single object — wrap in array
            return [self._normalize_row(data)]

        return []

    def _normalize_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a single row, flattening nested structures."""
        out = {}

        for key, value in row.items():
            # Skip metadata fields
            if key in ("Type", "Class", "Flags", "Name"):
                if key == "Name":
                    out["id"] = self._slugify(value)
                    out["name"] = value
                continue

            # Handle Properties dict (nested one level)
            if key == "Properties" and isinstance(value, dict):
                for prop_key, prop_value in value.items():
                    out[self._snake_case(prop_key)] = self._flatten_value(
                        prop_value
                    )
            else:
                out[self._snake_case(key)] = self._flatten_value(value)

        # Add type category if provided
        if self.type_category:
            out["_type"] = self.type_category

        return out

    def _flatten_value(self, value: Any) -> Any:
        """Flatten nested UAsset structures and resolve references."""
        if value is None:
            return None

        # Scalar types
        if isinstance(value, (bool, int, float, str)):
            return value

        # UAsset reference: { 'ObjectName': '...', 'ObjectPath': '...' }
        if isinstance(value, dict):
            # Check if it's a soft reference
            if "ObjectName" in value and "ObjectPath" in value:
                # Extract the asset name from ObjectPath
                path = value.get("ObjectPath", "")
                name = value.get("ObjectName", "").split("'")[0]
                # Return a simple reference string
                return {"asset_name": name, "asset_path": path}

            # Check if it's an enum: { 'EnumType': '...', 'Value': '...' }
            if "EnumType" in value and "Value" in value:
                enum_type = value.get("EnumType", "").split("::")[-1]
                enum_val = value.get("Value", "").split("::")[-1]
                return {"enum_type": enum_type, "enum_value": enum_val}

            # Nested struct: recurse and flatten
            if len(value) > 0:
                flattened = {}
                for k, v in value.items():
                    flattened[self._snake_case(k)] = self._flatten_value(v)
                return flattened

            return {}

        # Array: recurse on each element
        if isinstance(value, list):
            return [self._flatten_value(item) for item in value]

        # Unknown type
        type_name = type(value).__name__
        if type_name not in self.unknown_types:
            self.unknown_types.add(type_name)
            print(f"[WARN] Unknown field type: {type_name} = {value}", file=sys.stderr)

        return value

    @staticmethod
    def _slugify(name: str) -> str:
        """Convert name to slug: 'My Item' -> 'my_item'."""
        return (
            name.lower()
            .strip()
            .replace(" ", "_")
            .replace("-", "_")
            .replace("__", "_")
        )

    @staticmethod
    def _snake_case(name: str) -> str:
        """Convert camelCase or PascalCase to snake_case."""
        import re

        # Insert underscore before uppercase letters (camelCase -> snake_case)
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def main():
    parser = argparse.ArgumentParser(
        description="Parse FModel DataTable JSONs into clean normalized arrays",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python parse_datatable.py weapons.json --type Items --output parsed_items.json
  python parse_datatable.py raw/**/Item*.json --type Weapons
        """,
    )

    parser.add_argument(
        "input",
        nargs="+",
        help="Input JSON file(s) or glob pattern",
    )
    parser.add_argument(
        "--type",
        default="",
        help="Category tag to add to output (e.g. Items, Monsters)",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Output JSON file (default: stdout or input_dir/parsed_*.json)",
    )
    parser.add_argument(
        "--combine",
        action="store_true",
        help="Combine multiple input files into a single output array",
    )

    args = parser.parse_args()

    dt_parser = DataTableParser(type_category=args.type)
    all_rows = []

    # Handle input files
    input_files = []
    for pattern in args.input:
        path = Path(pattern)
        if "*" in pattern:
            # Glob pattern
            import glob

            input_files.extend(glob.glob(pattern, recursive=True))
        elif path.is_file():
            input_files.append(str(path))

    if not input_files:
        print(f"[ERROR] No input files found", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] Parsing {len(input_files)} file(s)", file=sys.stderr)

    for input_file in input_files:
        try:
            rows = dt_parser.parse_file(input_file)
            all_rows.extend(rows)
            print(f"[OK] {input_file}: {len(rows)} rows", file=sys.stderr)
        except Exception as e:
            print(f"[ERROR] {input_file}: {e}", file=sys.stderr)

    # Determine output
    if args.output:
        output_file = args.output
    elif args.combine:
        output_file = "parsed_combined.json"
    elif len(input_files) == 1:
        # Single input: output next to it
        input_path = Path(input_files[0])
        output_file = input_path.parent / f"parsed_{input_path.stem}.json"
    else:
        output_file = "parsed_output.json"

    # Write output
    output_data = all_rows if args.combine or len(input_files) > 1 else all_rows

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"[OK] Wrote {len(all_rows)} rows to {output_file}", file=sys.stderr)

    # Report unknown types
    if dt_parser.unknown_types:
        print(
            f"[WARN] Found unknown field types: {', '.join(sorted(dt_parser.unknown_types))}",
            file=sys.stderr,
        )

    # Output to stdout if no output file specified
    if not args.output and not args.combine and len(input_files) == 1:
        print(json.dumps(all_rows, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
