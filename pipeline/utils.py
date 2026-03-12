"""
Backwards-compatible shim. New code should import from pipeline.core directly.
This module re-exports core/ helpers for scripts that still reference utils.py.
"""
import json
from pathlib import Path

from pipeline.core.reader import load, find_files
from pipeline.core.normalizer import flatten, camel_to_snake
from pipeline.core.writer import Writer as _Writer

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "raw"
EXTRACTED_DIR = REPO_ROOT / "extracted"


def read_raw(relative_path: str) -> dict:
    """Read a JSON file from raw/ and return parsed data."""
    path = RAW_DIR / relative_path
    if not path.exists():
        raise FileNotFoundError(f"Raw file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_raw_files(pattern: str) -> list[Path]:
    """Glob for files in raw/ matching a pattern."""
    return sorted(RAW_DIR.glob(pattern))


def slugify(name: str) -> str:
    return name.lower().strip().replace(" ", "_").replace("-", "_")


def write_extracted(domain: str, filename: str, data: dict, source_path: str = ""):
    """Legacy writer — new code should use pipeline.core.writer.Writer."""
    writer = _Writer(EXTRACTED_DIR, pipeline_version="0.1.0")
    writer.write_entity(domain, filename, data, source_files=[source_path] if source_path else [])


def write_extracted_index(domain: str, entries: list[dict]):
    """Legacy index writer."""
    writer = _Writer(EXTRACTED_DIR, pipeline_version="0.1.0")
    writer.write_index(domain, entries)


def flatten_uasset(value):
    """Legacy name — delegates to pipeline.core.normalizer.flatten."""
    return flatten(value)


def snake_case(name: str) -> str:
    """Legacy name — delegates to pipeline.core.normalizer.camel_to_snake."""
    return camel_to_snake(name)
