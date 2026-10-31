#!/usr/bin/env python3
import os, runpy, sys
sys.argv[0] = "mc"
runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "mc.py"), run_name="__main__")
