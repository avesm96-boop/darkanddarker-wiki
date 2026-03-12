"""Tests for pipeline/extract_all.py orchestrator."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pipeline.extract_all import (
    PHASES,
    _ALL_DOMAINS,
    find_downstream_phases,
    should_skip_domain,
    run_pipeline,
    _parse_args,
)


@pytest.fixture()
def raw_root(tmp_path: Path) -> Path:
    r = tmp_path / "raw"
    r.mkdir()
    return r


@pytest.fixture()
def extracted_root(tmp_path: Path) -> Path:
    e = tmp_path / "extracted"
    e.mkdir()
    return e


def _make_raw_file(raw_root: Path, v2_subpath: str, filename: str = "data.json") -> Path:
    v2_base = raw_root / "DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2"
    target = v2_base / v2_subpath
    target.mkdir(parents=True, exist_ok=True)
    f = target / filename
    f.write_text("[]", encoding="utf-8")
    return f


def _make_index(extracted_root: Path, domain: str) -> Path:
    d = extracted_root / domain
    d.mkdir(parents=True, exist_ok=True)
    idx = d / "_index.json"
    idx.write_text(json.dumps({"count": 1, "entries": []}), encoding="utf-8")
    return idx


class TestShouldSkipDomain:
    def test_returns_false_when_index_missing(self, raw_root, extracted_root):
        _make_raw_file(raw_root, "Quest/Quest", "Id_Quest_01.json")
        assert should_skip_domain("quests", raw_root, extracted_root, force=False) is False

    def test_returns_true_when_index_newer_than_raw(self, raw_root, extracted_root):
        raw_file = _make_raw_file(raw_root, "Quest/Quest", "Id_Quest_01.json")
        time.sleep(0.05)
        idx = _make_index(extracted_root, "quests")
        assert idx.stat().st_mtime >= raw_file.stat().st_mtime
        assert should_skip_domain("quests", raw_root, extracted_root, force=False) is True

    def test_returns_false_when_raw_newer_than_index(self, raw_root, extracted_root):
        _make_index(extracted_root, "quests")
        time.sleep(0.05)
        _make_raw_file(raw_root, "Quest/Quest", "Id_Quest_01.json")
        assert should_skip_domain("quests", raw_root, extracted_root, force=False) is False

    def test_returns_false_when_force_true_even_if_index_newer(self, raw_root, extracted_root):
        _make_raw_file(raw_root, "Quest/Quest", "Id_Quest_01.json")
        time.sleep(0.05)
        _make_index(extracted_root, "quests")
        assert should_skip_domain("quests", raw_root, extracted_root, force=True) is False

    def test_returns_false_when_no_raw_files_exist(self, raw_root, extracted_root):
        _make_index(extracted_root, "quests")
        assert should_skip_domain("quests", raw_root, extracted_root, force=False) is False


class TestFindDownstreamPhases:
    def test_engine_returns_all_phases(self):
        result = find_downstream_phases("engine")
        assert result == list(range(len(PHASES)))

    def test_items_returns_from_phase1(self):
        result = find_downstream_phases("items")
        assert result == list(range(1, len(PHASES)))

    def test_quests_returns_last_phase_only(self):
        last_idx = len(PHASES) - 1
        result = find_downstream_phases("quests")
        assert result == [last_idx]

    def test_economy_returns_correct_phase(self):
        result = find_downstream_phases("economy")
        assert result == [4, 5]

    def test_unknown_domain_returns_empty_list(self):
        result = find_downstream_phases("nonexistent_domain")
        assert result == []

    def test_all_domains_found_in_phases(self):
        for domain in _ALL_DOMAINS:
            result = find_downstream_phases(domain)
            assert len(result) > 0, f"Domain '{domain}' not found in PHASES"


class TestArgParsing:
    def test_defaults_when_no_flags(self):
        args = _parse_args([])
        assert args.domain is None
        assert args.force is False
        assert args.raw is None
        assert args.out is None

    def test_force_flag(self):
        args = _parse_args(["--force"])
        assert args.force is True
        assert args.domain is None

    def test_domain_flag(self):
        args = _parse_args(["--domain", "items"])
        assert args.domain == "items"
        assert args.force is False

    def test_force_and_domain_together(self):
        args = _parse_args(["--force", "--domain", "combat"])
        assert args.force is True
        assert args.domain == "combat"

    def test_raw_and_out_flags(self):
        args = _parse_args(["--raw", "/tmp/raw", "--out", "/tmp/out"])
        assert args.raw == "/tmp/raw"
        assert args.out == "/tmp/out"


def _make_import_side_effect(extracted_root: Path, fail_domain: str | None = None):
    """Return a side_effect fn for importlib.import_module."""
    called = []

    def _import(module_path: str):
        domain = module_path.split(".")[-1]
        mock_mod = MagicMock()

        def _run(raw_root, extracted_root):
            called.append(domain)
            if domain == fail_domain:
                raise RuntimeError(f"{domain} extraction failed")
            d = extracted_root / domain
            d.mkdir(parents=True, exist_ok=True)
            (d / "_index.json").write_text("{}", encoding="utf-8")
            return {"entities": 1}

        mock_mod.run = _run
        return mock_mod

    return _import, called


class TestRunPipelineIntegration:
    def _resolver_patch(self):
        import pipeline.core.resolver as res_mod
        return patch.object(res_mod.Resolver, "load_domain")

    def _skip_patch(self, **kwargs):
        """Patch should_skip_domain via patch.object to avoid interaction with
        the importlib.import_module patch which replaces pipeline.extract_all.importlib
        and breaks string-based patch lookups on the same module."""
        import pipeline.extract_all as ea_mod
        return patch.object(ea_mod, "should_skip_domain", **kwargs)

    def test_all_phases_run_when_no_skip(self, raw_root, extracted_root):
        _import, called = _make_import_side_effect(extracted_root)
        with patch("pipeline.extract_all.importlib.import_module", side_effect=_import):
            with self._skip_patch(return_value=False):
                with self._resolver_patch():
                    exit_code = run_pipeline(raw_root, extracted_root)
        assert exit_code == 0
        assert set(called) == set(_ALL_DOMAINS)

    def test_phase_execution_order_respects_phases(self, raw_root, extracted_root):
        _import, call_order = _make_import_side_effect(extracted_root)
        with patch("pipeline.extract_all.importlib.import_module", side_effect=_import):
            with self._skip_patch(return_value=False):
                with self._resolver_patch():
                    run_pipeline(raw_root, extracted_root)
        engine_idx = call_order.index("engine")
        for d in {"items", "classes", "monsters"}:
            if d in call_order:
                assert call_order.index(d) > engine_idx

    def test_skip_logic_prevents_domain_run(self, raw_root, extracted_root):
        _import, called = _make_import_side_effect(extracted_root)

        def _skip(domain, raw_root, extracted_root, force=False):
            d = extracted_root / domain
            d.mkdir(parents=True, exist_ok=True)
            (d / "_index.json").write_text("{}", encoding="utf-8")
            return True

        with patch("pipeline.extract_all.importlib.import_module", side_effect=_import):
            with self._skip_patch(side_effect=_skip):
                exit_code = run_pipeline(raw_root, extracted_root)
        assert exit_code == 0
        assert called == []

    def test_failure_in_phase_blocks_downstream_phases(self, raw_root, extracted_root):
        _import, called = _make_import_side_effect(extracted_root, fail_domain="engine")
        with patch("pipeline.extract_all.importlib.import_module", side_effect=_import):
            with self._skip_patch(return_value=False):
                with self._resolver_patch():
                    exit_code = run_pipeline(raw_root, extracted_root)
        assert exit_code == 1
        phase2_plus = {"items", "classes", "monsters", "combat", "spells", "status",
                       "dungeons", "spawns", "economy", "quests"}
        assert set(called).isdisjoint(phase2_plus)

    def test_failure_in_phase2_blocks_phases_3_plus_not_phase1(self, raw_root, extracted_root):
        _import, called = _make_import_side_effect(extracted_root, fail_domain="items")
        with patch("pipeline.extract_all.importlib.import_module", side_effect=_import):
            with self._skip_patch(return_value=False):
                with self._resolver_patch():
                    exit_code = run_pipeline(raw_root, extracted_root)
        assert exit_code == 1
        assert "engine" in called
        phase3_plus = {"combat", "spells", "status", "dungeons", "spawns", "economy", "quests"}
        assert set(called).isdisjoint(phase3_plus)

    def test_domain_flag_forces_target_and_downstream(self, raw_root, extracted_root):
        _import, called = _make_import_side_effect(extracted_root)

        def _fake_skip(domain, raw_root, extracted_root, force=False):
            if domain == "engine":
                idx = extracted_root / "engine" / "_index.json"
                idx.parent.mkdir(parents=True, exist_ok=True)
                idx.write_text("{}", encoding="utf-8")
                return True
            return False

        with patch("pipeline.extract_all.importlib.import_module", side_effect=_import):
            with self._skip_patch(side_effect=_fake_skip):
                with self._resolver_patch():
                    exit_code = run_pipeline(raw_root, extracted_root, force=False, target_domain="items")
        assert exit_code == 0
        assert "engine" not in called
        downstream = {d for i, phase in enumerate(PHASES) for d in phase if i >= 1}
        assert downstream.issubset(set(called))

    def test_force_flag_bypasses_skip_for_all_domains(self, raw_root, extracted_root):
        _import, _ = _make_import_side_effect(extracted_root)
        skip_force_values = []

        def _fake_skip(domain, raw_root, extracted_root, force=False):
            skip_force_values.append(force)
            return False

        with patch("pipeline.extract_all.importlib.import_module", side_effect=_import):
            with self._skip_patch(side_effect=_fake_skip):
                with self._resolver_patch():
                    run_pipeline(raw_root, extracted_root, force=True)
        assert all(v is True for v in skip_force_values)
