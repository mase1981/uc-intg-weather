"""
Entry point wrapper for the Weather integration.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

import asyncio

from uc_intg_weather import main

if __name__ == "__main__":
    asyncio.run(main())
