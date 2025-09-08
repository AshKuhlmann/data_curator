"""Test configuration for the suite.

Ensures the local package source is importable ahead of any globally
installed version so tests run against the current workspace code.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
