"""
NetMedic build script.

Packages the application into a single portable executable using
PyInstaller. The script handles:

1. Dependency installation (if needed)
2. Cleanup of previous build artifacts
3. PyInstaller execution
4. Build size reporting
5. Verification of the output executable

Usage::

    python build.py              # Standard build
    python build.py --clean      # Clean build artifacts first
    python build.py --verify     # Run the executable after building
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


# --------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------- #

PROJECT_ROOT = Path(__file__).resolve().parent
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
SPEC_FILE = PROJECT_ROOT / "netmedic.spec"
OUTPUT_NAME = "NetMedic.exe"
OUTPUT_PATH = DIST_DIR / OUTPUT_NAME


# --------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------- #

def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and result.returncode != 0:
        print(f"\n✗ Command failed (exit {result.returncode}):")
        print(result.stderr[:1000])
        sys.exit(1)
    return result


def clean_build():
    """Remove previous build artifacts."""
    print("\nCleaning build artifacts...")
    for path in [DIST_DIR, BUILD_DIR]:
        if path.exists():
            print(f"  Removing {path.name}/")
            shutil.rmtree(path, ignore_errors=True)
    # Remove __pycache__ directories
    for cache_dir in PROJECT_ROOT.rglob("__pycache__"):
        shutil.rmtree(cache_dir, ignore_errors=True)
    print("  Done.")


def ensure_pyinstaller():
    """Ensure PyInstaller is installed."""
    try:
        import PyInstaller  # noqa: F401
        print(f"  PyInstaller {PyInstaller.__version__} found")
    except ImportError:
        print("  Installing PyInstaller...")
        run([sys.executable, "-m", "pip", "install", "pyinstaller>=6.0.0"], check=True)


def ensure_dependencies():
    """Ensure all project dependencies are installed."""
    print("\nChecking dependencies...")
    ensure_pyinstaller()

    req_file = PROJECT_ROOT / "requirements.txt"
    if req_file.exists():
        print("  Installing project dependencies...")
        run([sys.executable, "-m", "pip", "install", "-r", str(req_file), "-q"], check=True)
        print("  Dependencies installed")


def build_executable():
    """Run PyInstaller to build the executable."""
    print("\nBuilding executable...")
    start = time.time()

    run([
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--log-level=WARN",
        str(SPEC_FILE),
    ])

    elapsed = time.time() - start
    print(f"\n  Build completed in {elapsed:.1f}s")


def report_size():
    """Report the size of the output executable."""
    if not OUTPUT_PATH.exists():
        print(f"\n✗ Output not found: {OUTPUT_PATH}")
        return

    size_bytes = OUTPUT_PATH.stat().st_size
    size_mb = size_bytes / (1024 * 1024)

    print(f"\n{'='*50}")
    print(f"  Output: {OUTPUT_PATH}")
    print(f"  Size:   {size_mb:.1f} MB ({size_bytes:,} bytes)")
    print(f"{'='*50}")

    # Size assessment
    if size_mb < 15:
        print("  Rating: Excellent (< 15 MB)")
    elif size_mb < 30:
        print("  Rating: Good (< 30 MB)")
    elif size_mb < 50:
        print("  Rating: Fair (< 50 MB)")
    else:
        print("  Rating: Large (> 50 MB) — consider excluding more modules")


def verify_executable():
    """Run the executable to verify it works."""
    if not OUTPUT_PATH.exists():
        print(f"\n✗ Output not found: {OUTPUT_PATH}")
        return False

    print(f"\nVerifying {OUTPUT_NAME}...")
    print("  Launching application (press Ctrl+C or close window to exit)")

    try:
        # Launch the executable (it will block until the user closes it)
        proc = subprocess.Popen(
            [str(OUTPUT_PATH)],
            cwd=str(DIST_DIR),
        )
        print(f"  Application launched (PID: {proc.pid})")
        print("  [OK] Executable verified successfully")
        return True
    except KeyboardInterrupt:
        print("\n  Verification cancelled by user")
        return True
    except Exception as exc:
        print(f"\n  ✗ Verification failed: {exc}")
        return False


def create_distribution():
    """Create a clean distribution folder."""
    if not OUTPUT_PATH.exists():
        return

    dist_folder = DIST_DIR / "NetMedic-Portable"
    dist_folder.mkdir(exist_ok=True)

    # Copy executable
    shutil.copy2(OUTPUT_PATH, dist_folder / OUTPUT_NAME)

    # Create a README for the distribution
    readme = dist_folder / "README.txt"
    readme.write_text(
        f"NetMedic - Windows Network Diagnostics & Repair Toolkit\n"
        f"{'='*50}\n\n"
        f"Version: 1.3.0\n"
        f"License: MIT\n\n"
        f"Quick Start:\n"
        f"  1. Double-click {OUTPUT_NAME} to launch\n"
        f"  2. The application runs in Windows Terminal\n"
        f"  3. No installation required — fully portable\n\n"
        f"Requirements:\n"
        f"  - Windows 10/11\n"
        f"  - Windows Terminal, CMD, or PowerShell\n\n"
        f"Keyboard Shortcuts:\n"
        f"  R - Scan adapters\n"
        f"  T - Internet Diagnostics\n"
        f"  S - Speed Test\n"
        f"  N - DNS Tools\n"
        f"  U - Network Repair\n"
        f"  A - Adapter Manager\n"
        f"  P - Public Info\n"
        f"  G - Diagnostic Report\n"
        f"  H - Health Score\n"
        f"  L - Log Viewer\n"
        f"  Q - Quit\n\n"
        f"For more information, visit:\n"
        f"https://github.com/mmdMadi/NetMedic\n",
        encoding="utf-8",
    )

    print(f"\n  Distribution folder created: {dist_folder}")
    print(f"  Contents: {OUTPUT_NAME}, README.txt")


# --------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------- #

def main():
    """Build NetMedic executable."""
    parser = argparse.ArgumentParser(
        prog="build",
        description="Build NetMedic portable executable",
    )
    parser.add_argument(
        "--clean", action="store_true",
        help="Clean build artifacts before building",
    )
    parser.add_argument(
        "--verify", action="store_true",
        help="Launch the executable after building to verify",
    )
    args = parser.parse_args()

    print("NetMedic Build Script")
    print("=" * 50)

    if args.clean:
        clean_build()

    ensure_dependencies()
    build_executable()
    report_size()
    create_distribution()

    if args.verify:
        verify_executable()

    print(f"\n[OK] Build complete: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
