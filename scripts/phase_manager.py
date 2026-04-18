#!/usr/bin/env python3
"""
Hardwareless AI — Phase Manager Launcher
Run: python scripts/phase_manager.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core_engine.setup_manager import main

if __name__ == "__main__":
    main()