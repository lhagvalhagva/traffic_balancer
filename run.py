#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Src директорийг Python зам руу нэмэх
BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

# Main импортлох
from src import main

if __name__ == "__main__":
    # Тухайн диреторид ажиллуулах
    os.chdir(str(BASE_DIR))
    # Командын мөрний аргументуудыг main-д дамжуулах
    sys.argv = [sys.argv[0]] + sys.argv[1:]
    main.main() 