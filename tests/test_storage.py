"""
Tests for on-disk storage and path resolution.

Covers Storage paths, read_json, and write_json using tmp_path fixtures.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from utils.storage import Storage


class TestStoragePaths:
    def test_base_dir(self, tmp_path: Path) -> None:
        s = Storage(base_dir=tmp_path)
        assert s.base_dir == tmp_path

    def test_logs_dir_created(self, tmp_path: Path) -> None:
        s = Storage(base_dir=tmp_path)
        logs = s.logs_dir
        assert logs.exists()
        assert logs.name == "logs"

    def test_config_path(self, tmp_path: Path) -> None:
        s = Storage(base_dir=tmp_path)
        assert s.config_path == tmp_path / "config.json"

    def test_theme_path(self, tmp_path: Path) -> None:
        s = Storage(base_dir=tmp_path)
        assert s.theme_path == tmp_path / "theme.tcss"


class TestReadJson:
    def test_missing_file_returns_default(self, tmp_path: Path) -> None:
        s = Storage(base_dir=tmp_path)
        result = s.read_json(tmp_path / "missing.json", default={"key": "val"})
        assert result == {"key": "val"}

    def test_valid_json(self, tmp_path: Path) -> None:
        f = tmp_path / "data.json"
        f.write_text('{"a": 1}', encoding="utf-8")
        s = Storage(base_dir=tmp_path)
        assert s.read_json(f) == {"a": 1}

    def test_invalid_json_returns_default(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.json"
        f.write_text("not json {{{", encoding="utf-8")
        s = Storage(base_dir=tmp_path)
        assert s.read_json(f, default=[]) == []


class TestWriteJson:
    def test_write_and_read(self, tmp_path: Path) -> None:
        s = Storage(base_dir=tmp_path)
        target = tmp_path / "out.json"
        assert s.write_json(target, {"hello": "world"})
        assert s.read_json(target) == {"hello": "world"}

    def test_atomic_write(self, tmp_path: Path) -> None:
        """Temp file should not exist after successful write."""
        s = Storage(base_dir=tmp_path)
        target = tmp_path / "atomic.json"
        s.write_json(target, [1, 2, 3])
        tmp = target.with_suffix(".json.tmp")
        assert not tmp.exists()

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        s = Storage(base_dir=tmp_path)
        target = tmp_path / "sub" / "dir" / "file.json"
        assert s.write_json(target, {"nested": True})
        assert s.read_json(target) == {"nested": True}
