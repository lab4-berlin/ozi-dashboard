# etl/lake.py - re-export common.lake for convenience within the etl module
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common.lake import *
