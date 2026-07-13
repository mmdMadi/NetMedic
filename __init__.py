"""
NetMedic
========

A professional Windows Network Adapter Manager built with Textual.

NetMedic inspects Windows network adapters, detects inactive, virtual,
VPN, and ghost adapters, and provides safe maintenance tools.

It NEVER automatically removes hardware. Every destructive operation
requires explicit user confirmation.

Public sub-packages
-------------------
- :mod:`netmedic.network` -- adapter scanning, categorization, PowerShell wrappers.
- :mod:`netmedic.ui`      -- Textual TUI widgets and screens.
- :mod:`netmedic.utils`   -- logging, config storage, admin detection, helpers.

Starting the application
------------------------
Run the project from the repository root::

    python app.py
"""

from __future__ import annotations

__version__ = "1.3.0"
__author__ = "NetMedic Contributors"
__license__ = "MIT"

__all__ = ["__version__", "__author__", "__license__"]
