# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for NetMedic.

Build with:
    pyinstaller netmedic.spec

Or use the build script:
    python build.py

The spec is tuned for:
- Single-file portable executable
- Small size (exclude unnecessary modules)
- Fast startup (no runtime extraction on launch)
- Windows-only (uses subprocess with CREATE_NO_WINDOW)
"""

import os
import sys
from pathlib import Path

# Project root
ROOT = Path(os.path.abspath(SPECPATH))

# Collect all Python source directories
src_dirs = [
    str(ROOT / "network"),
    str(ROOT / "ui"),
    str(ROOT / "utils"),
]

a = Analysis(
    [str(ROOT / "app.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "theme.tcss"), "."),
        (str(ROOT / "config.json"), "."),
        (str(ROOT / "__init__.py"), "."),
    ],
    hiddenimports=[
        "network",
        "network.powershell",
        "network.adapter",
        "network.categorizer",
        "network.scanner",
        "network.diagnostics",
        "network.export",
        "network.internet",
        "network.local_info",
        "network.public_info",
        "network.health",
        "network.diagnostics_internet",
        "network.speed_test",
        "network.dns_tools",
        "network.repair",
        "network.adapter_manager",
        "network.report_generator",
        "network.health_service",
        "ui",
        "ui.dashboard",
        "ui.adapter_table",
        "ui.details",
        "ui.status",
        "ui.actions_bar",
        "ui.dialogs",
        "ui.diagnostics",
        "ui.speed_test",
        "ui.dns_tools",
        "ui.repair",
        "ui.adapter_manager",
        "ui.public_info",
        "ui.report_generator",
        "ui.health_score",
        "ui.log_viewer",
        "utils",
        "utils.admin",
        "utils.logger",
        "utils.helpers",
        "utils.storage",
        "config",
        "psutil",
        "requests",
        "textual",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        "tkinter",
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "PIL",
        "cv2",
        "torch",
        "tensorflow",
        "pytest",
        "unittest",
        "doctest",
        "xmlrpc",
        "pydoc",
        "pdb",
        "profile",
        "cProfile",
        "timeit",
        "lib2to3",
        "ensurepip",
        "idlelib",
        "turtledemo",
        "test",
        "tests",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="NetMedic",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window (TUI runs in Windows Terminal)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon=None or path to .ico file
)
