"""Cross-domain ID linker and enum resolver."""
import json
import threading
from pathlib import Path


class Resolver:
    """
    Thread safety contract:
    - register() and load_domain() MUST be called from the main orchestrator thread only.
    - resolve() and resolve_enum() are safe to call concurrently from worker threads.
    """

    def __init__(self):
        self._registry: dict[str, dict] = {}
        self._enums: dict[str, dict] = {}
        self._lock = threading.Lock()

    def register(self, domain: str, id_: str, record: dict) -> None:
        """Add a record to the in-memory registry. Orchestrator-thread only."""
        with self._lock:
            self._registry[id_] = record

    def resolve(self, asset_id: str) -> dict | None:
        """Lookup a record by asset name or path. Safe to call from worker threads."""
        with self._lock:
            return self._registry.get(asset_id)

    def resolve_enum(self, enum_name: str, index: int) -> str | None:
        """Return displayName for enum_name at index, or None if not found."""
        enum = self._enums.get(enum_name)
        if not enum:
            return None
        for entry in enum.get("values", []):
            if entry.get("index") == index:
                return entry.get("displayName")
        return None

    def load_enums(self, enums_path: Path) -> None:
        """Load extracted/engine/enums.json into the enum lookup table."""
        with open(enums_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._enums = data

    def load_domain(self, domain: str, extracted_root: Path) -> None:
        """Hydrate registry from all entity files in extracted/<domain>/. Orchestrator-thread only.

        NOTE: Does NOT load enums. Call load_enums() separately for enum label resolution.
        The spec's 'resolver.load_domain("engine")' example refers to entity hydration only.
        """
        domain_dir = extracted_root / domain
        if not domain_dir.exists():
            return
        for json_file in sorted(domain_dir.glob("*.json")):
            if json_file.name.startswith("_"):
                continue
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    record = json.load(f)
                entity_id = json_file.stem
                self.register(domain, entity_id, record)
            except (json.JSONDecodeError, IOError):
                continue
