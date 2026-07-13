"""
Tests for admin detection utilities.

Covers ElevationInfo, is_admin, and get_elevation_info.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from utils.admin import ElevationInfo, get_elevation_info, is_admin


class TestElevationInfo:
    def test_admin_text(self) -> None:
        info = ElevationInfo(is_admin=True, platform="win32", detail="Admin")
        assert "Administrator" in info.as_text()

    def test_standard_text(self) -> None:
        info = ElevationInfo(is_admin=False, platform="win32", detail="Standard")
        assert "Standard user" in info.as_text()

    def test_frozen(self) -> None:
        info = ElevationInfo(is_admin=True, platform="linux", detail="test")
        with pytest.raises(AttributeError):
            info.is_admin = False  # type: ignore[misc]


class TestIsAdmin:
    def test_returns_bool(self) -> None:
        result = is_admin()
        assert isinstance(result, bool)

    def test_does_not_crash(self) -> None:
        """is_admin() must never raise, regardless of platform."""
        assert is_admin() in {True, False}


class TestGetElevationInfo:
    def test_returns_info(self) -> None:
        info = get_elevation_info()
        assert isinstance(info, ElevationInfo)
        assert isinstance(info.is_admin, bool)

    def test_has_platform(self) -> None:
        info = get_elevation_info()
        assert info.platform in {"win32", "linux", "darwin"}
