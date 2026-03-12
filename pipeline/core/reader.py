"""Raw JSON loading and glob helpers for the extraction pipeline."""
import glob as _glob
import json
from pathlib import Path


def load(path: Path) -> list[dict]:
    """Parse one raw JSON file, returning a list of UE5 export objects."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}") from e
    return data if isinstance(data, list) else [data]


def find_files(pattern: str) -> list[Path]:
    """Find all files matching a glob pattern, returned sorted."""
    return sorted(Path(p) for p in _glob.glob(pattern, recursive=True))


def find_by_type(type_name: str, search_dir: Path) -> list[Path]:
    """Scan search_dir recursively for JSON files containing objects of the given Type."""
    results = []
    for json_file in sorted(Path(search_dir).rglob("*.json")):
        try:
            data = load(json_file)
        except (FileNotFoundError, ValueError):
            continue
        if any(isinstance(obj, dict) and obj.get("Type") == type_name for obj in data):
            results.append(json_file)
    return results


def get_properties(obj: dict) -> dict:
    """Safely extract obj['Properties'], returning {} if absent."""
    result = obj.get("Properties")
    return result if isinstance(result, dict) else {}


def get_item(obj: dict) -> dict:
    """Safely extract obj['Properties']['Item'], returning {} if absent."""
    result = get_properties(obj).get("Item")
    return result if isinstance(result, dict) else {}
