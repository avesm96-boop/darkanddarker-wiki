"""Standardized output writers for the extraction pipeline."""
import json
from datetime import datetime, timezone
from pathlib import Path


class Writer:
    def __init__(self, extracted_root: Path, pipeline_version: str = "1.0.0"):
        self.extracted_root = Path(extracted_root)
        self.pipeline_version = pipeline_version

    def _meta(self, source_files: list[str]) -> dict:
        return {
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "source_files": list(source_files),
            "pipeline_version": self.pipeline_version,
        }

    def _write(self, path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def write_entity(self, domain: str, id_: str, data: dict, source_files: list[str]) -> Path:
        """Write extracted/<domain>/<id>.json with _meta appended."""
        out = {k: v for k, v in data.items() if k != "_meta"}
        out["_meta"] = self._meta(source_files)
        path = self.extracted_root / domain / f"{id_}.json"
        self._write(path, out)
        return path

    def write_index(self, domain: str, entries: list[dict]) -> Path:
        """Write extracted/<domain>/_index.json."""
        data = {
            "count": len(entries),
            "entries": entries,
            "_meta": self._meta([]),
        }
        path = self.extracted_root / domain / "_index.json"
        self._write(path, data)
        return path

    def write_system(self, domain: str, name: str, data: dict, source_files: list[str]) -> Path:
        """Write extracted/<domain>/<name>.json for non-entity system files."""
        out = {k: v for k, v in data.items() if k != "_meta"}
        out["_meta"] = self._meta(source_files)
        path = self.extracted_root / domain / f"{name}.json"
        self._write(path, out)
        return path
