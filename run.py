#!/usr/bin/env python3
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from src import main

if __name__ == "__main__":
    os.chdir(str(BASE_DIR))
    sys.argv = [sys.argv[0]] + sys.argv[1:]
    main.main() 