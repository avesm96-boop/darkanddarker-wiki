"""Extract CT_ CurveTable and CurveFloat assets -> extracted/engine/curves.json."""
from pathlib import Path

from pipeline.core.reader import load, find_files
from pipeline.core.writer import Writer


def extract_curve_table(file_path: Path) -> dict | None:
    """Extract one CT_ CurveTable into normalized form."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "CurveTable"), None)
    if not obj:
        return None

    rows = {}
    for attr_name, curve in (obj.get("Rows") or {}).items():
        keys = [{"time": k.get("Time", 0), "value": k.get("Value", 0)}
                for k in (curve.get("Keys") or [])]
        rows[attr_name] = {
            "interp_mode": curve.get("InterpMode", "RCIM_Linear"),
            "keys": keys,
        }

    return {
        "name": obj.get("Name", file_path.stem),
        "rows": rows,
        "source_file": str(file_path),
    }


def extract_curve_float(file_path: Path) -> dict | None:
    """Extract one CurveFloat asset into normalized form."""
    try:
        data = load(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

    obj = next((o for o in data if isinstance(o, dict)
                and o.get("Type") == "CurveFloat"), None)
    if not obj:
        return None

    raw_keys = (obj.get("Properties", {}).get("FloatCurve") or {}).get("Keys", [])
    keys = [{"time": k.get("Time", 0), "value": k.get("Value", 0)} for k in raw_keys]

    return {
        "name": obj.get("Name", file_path.stem),
        "keys": keys,
        "source_file": str(file_path),
    }


def run_curves(curve_dirs: list[Path], extracted_root: Path) -> dict:
    """Extract CT_ curve tables and CurveFloat assets -> extracted/engine/curves.json."""
    curve_tables = {}
    curve_floats = {}
    source_files = []

    for curve_dir in curve_dirs:
        ct_files = find_files(str(Path(curve_dir) / "CT_*.json"))
        print(f"  [curves] Found {len(ct_files)} CT_ files in {curve_dir}")
        for f in ct_files:
            result = extract_curve_table(f)
            if result:
                curve_tables[result["name"]] = {"rows": result["rows"]}
                source_files.append(result["source_file"])

        # CurveFloat assets may appear alongside CT_ tables or in other dirs
        for f in find_files(str(Path(curve_dir) / "*.json")):
            result = extract_curve_float(f)
            if result:
                curve_floats[result["name"]] = {"keys": result["keys"]}
                source_files.append(result["source_file"])

    writer = Writer(extracted_root)
    writer.write_system("engine", "curves",
                        {"curve_tables": curve_tables, "curve_floats": curve_floats},
                        source_files=source_files)
    print(f"  [curves] Extracted {len(curve_tables)} curve tables, {len(curve_floats)} curve floats")
    return {"curve_tables": curve_tables, "curve_floats": curve_floats}
