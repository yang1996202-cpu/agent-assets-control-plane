import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
LIB_DIR = os.path.join(ROOT, "lib")
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)
