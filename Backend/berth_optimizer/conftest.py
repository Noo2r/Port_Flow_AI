import sys
from pathlib import Path

# Makes 'berth_optimizer' importable from anywhere pytest is run
sys.path.insert(0, str(Path(__file__).parent.parent))
