import sys
import os

# Add root directory to sys.path so backend package is always discoverable
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Import backend to register all subpackage aliases in sys.modules
import backend
