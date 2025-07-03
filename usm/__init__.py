import sys
from pathlib import Path

# Add Verdant source directories to path for module imports
SRC_PARENT = Path(__file__).resolve().parent.parent / 'Verdant Source Codes'
SRC_PATH = SRC_PARENT / 'src'
for p in (SRC_PARENT, SRC_PATH):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

# Import UnifiedSystem using the full package path so relative imports work
from src.core.system import UnifiedSystem as UnifiedSyntheticMind

__all__ = ["UnifiedSyntheticMind"]
