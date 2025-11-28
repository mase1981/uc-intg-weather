"""
Weather Integration for Unfolded Circle Remote Two/3.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import json
import os


def _get_version():
    """Get version from driver.json file."""
    try:
        driver_path = os.path.join(os.path.dirname(__file__), "..", "driver.json")
        with open(driver_path, 'r', encoding='utf-8') as f:
            driver_data = json.load(f)
            return driver_data.get('version', 'unknown')
    except Exception:
        return "unknown"


__version__ = _get_version()
version_tuple = tuple(__version__.split('.')) if __version__ != "unknown" else (0, 0, "unknown")

__all__ = ["__version__", "version_tuple"]