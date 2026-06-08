"""Central project paths, so modules never hardcode folder locations."""
import os

SRC_DIR = os.path.dirname(os.path.abspath(__file__))   # ...\jarvis\src
ROOT = os.path.dirname(SRC_DIR)                          # ...\jarvis
DATA = os.path.join(ROOT, "data")                        # runtime data (gitignored)
VENV = os.path.join(ROOT, "venv")

os.makedirs(DATA, exist_ok=True)
