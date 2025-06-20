import sys
from pathlib import Path

# Add src directory to path for module imports
SRC_PATH = Path(__file__).resolve().parent.parent / 'Verdant Source Codes' / 'src'
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from core.system import UnifiedSystem as UnifiedSyntheticMind

__all__ = ["UnifiedSyntheticMind"]
