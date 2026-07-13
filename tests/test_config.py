"""
Tests for the Config dataclass.

Covers construction, validation, coercion, save/load, and mutators.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from config import Config


class TestConfigDefaults:
    def test_defaults(self) -> None:
        c = Config()
        assert c.theme == "netmedic-dark"
        assert c.scan_timeout == 60
        assert c.logging is True
        assert c.ignored_adapters == []


class TestConfigCoercion:
    def test_set_timeout_clamped_min(self) -> None:
        c = Config()
        c.set_timeout(1)
        assert c.scan_timeout == 5

    def test_set_timeout_clamped_max(self) -> None:
        c = Config()
        c.set_timeout(9999)
        assert c.scan_timeout == 600

    def test_timeout_string_coerced(self) -> None:
        c = Config()
        c.set_timeout("30")
        assert c.scan_timeout == 30

    def test_timeout_invalid_coerced(self) -> None:
        c = Config()
        c.set_timeout("bad")
        assert c.scan_timeout == 60

    def test_constructor_stores_raw(self) -> None:
        """Constructor does not validate; set_timeout() does."""
        c = Config(scan_timeout=1)
        assert c.scan_timeout == 1


class TestConfigMutators:
    def test_set_theme(self) -> None:
        c = Config()
        c.set_theme("dark")
        assert c.theme == "dark"

    def test_set_theme_empty_ignored(self) -> None:
        c = Config()
        c.set_theme("")
        assert c.theme == "netmedic-dark"

    def test_ignore(self) -> None:
        c = Config()
        c.ignore("Wi-Fi")
        assert "Wi-Fi" in c.ignored_adapters

    def test_ignore_no_duplicates(self) -> None:
        c = Config()
        c.ignore("Wi-Fi")
        c.ignore("Wi-Fi")
        assert c.ignored_adapters.count("Wi-Fi") == 1

    def test_unignore(self) -> None:
        c = Config(ignored_adapters=["Wi-Fi"])
        c.unignore("Wi-Fi")
        assert "Wi-Fi" not in c.ignored_adapters

    def test_is_ignored(self) -> None:
        c = Config(ignored_adapters=["Wi-Fi"])
        assert c.is_ignored("Wi-Fi") is True
        assert c.is_ignored("Eth") is False


class TestConfigSerialization:
    def test_to_dict(self) -> None:
        c = Config()
        d = c.to_dict()
        assert d["theme"] == "netmedic-dark"
        assert d["scan_timeout"] == 60

    def test_to_json(self) -> None:
        c = Config()
        j = c.to_json()
        assert "netmedic-dark" in j


class TestConfigPersistence:
    def test_save_and_load(self, tmp_path: Path) -> None:
        from utils.storage import Storage
        storage = Storage(base_dir=tmp_path)
        c = Config(theme="custom", scan_timeout=30)
        assert c.save(storage)

        loaded = Config.from_storage(storage)
        assert loaded.theme == "custom"
        assert loaded.scan_timeout == 30

    def test_missing_file_uses_defaults(self, tmp_path: Path) -> None:
        from utils.storage import Storage
        storage = Storage(base_dir=tmp_path)
        loaded = Config.from_storage(storage)
        assert loaded.theme == "netmedic-dark"
