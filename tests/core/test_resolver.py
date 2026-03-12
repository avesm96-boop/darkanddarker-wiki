"""Tests for pipeline/core/resolver.py"""
import json
import pytest
from pathlib import Path
from pipeline.core.resolver import Resolver


@pytest.fixture
def resolver():
    return Resolver()


def test_register_and_resolve(resolver):
    resolver.register("items", "longsword", {"name": "Longsword"})
    result = resolver.resolve("longsword")
    assert result == {"name": "Longsword"}


def test_resolve_returns_none_for_unknown(resolver):
    assert resolver.resolve("unknown_asset") is None


def test_register_overwrites_existing(resolver):
    resolver.register("items", "sword", {"name": "Sword v1"})
    resolver.register("items", "sword", {"name": "Sword v2"})
    # Last write wins (register is idempotent for updates)
    assert resolver.resolve("sword")["name"] == "Sword v2"


def test_resolve_enum_returns_display_name(tmp_path, resolver):
    enums_data = {
        "E_DamageType": {
            "values": [
                {"index": 0, "name": "NewEnumerator0", "displayName": "Physical"},
                {"index": 1, "name": "NewEnumerator1", "displayName": "Magic"}
            ]
        }
    }
    enums_file = tmp_path / "enums.json"
    enums_file.write_text(json.dumps(enums_data), encoding="utf-8")
    resolver.load_enums(enums_file)
    assert resolver.resolve_enum("E_DamageType", 1) == "Magic"


def test_resolve_enum_returns_none_for_unknown_enum(resolver):
    assert resolver.resolve_enum("E_Unknown", 0) is None


def test_resolve_enum_returns_none_for_unknown_index(tmp_path, resolver):
    enums_data = {"E_Foo": {"values": [{"index": 0, "name": "A", "displayName": "Alpha"}]}}
    enums_file = tmp_path / "enums.json"
    enums_file.write_text(json.dumps(enums_data), encoding="utf-8")
    resolver.load_enums(enums_file)
    assert resolver.resolve_enum("E_Foo", 99) is None


def test_load_domain_hydrates_registry(tmp_path, resolver):
    domain_dir = tmp_path / "items"
    domain_dir.mkdir()
    sword = {"id": "sword", "name": "Sword"}
    (domain_dir / "sword.json").write_text(json.dumps(sword), encoding="utf-8")
    # _index.json should be skipped
    index = {"count": 1, "entries": []}
    (domain_dir / "_index.json").write_text(json.dumps(index), encoding="utf-8")
    resolver.load_domain("items", tmp_path)
    assert resolver.resolve("sword") == sword


def test_load_domain_skips_index_file(tmp_path, resolver):
    domain_dir = tmp_path / "items"
    domain_dir.mkdir()
    index = {"count": 0, "entries": []}
    (domain_dir / "_index.json").write_text(json.dumps(index), encoding="utf-8")
    resolver.load_domain("items", tmp_path)
    assert resolver.resolve("_index") is None


def test_concurrent_reads_are_safe(resolver):
    """register() from main thread, resolve() concurrent reads — no crash."""
    import threading
    resolver.register("items", "sword", {"name": "Sword"})
    errors = []

    def read_worker():
        try:
            for _ in range(100):
                resolver.resolve("sword")
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=read_worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
