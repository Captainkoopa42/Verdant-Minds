import sys
from pathlib import Path

# Add src directory to path for module imports
SRC_PARENT = Path(__file__).resolve().parent.parent / 'Verdant Source Codes'
if str(SRC_PARENT) not in sys.path:
    sys.path.insert(0, str(SRC_PARENT))

from src.core.system import UnifiedSystem as UnifiedSyntheticMind

__all__ = ["UnifiedSyntheticMind"]
