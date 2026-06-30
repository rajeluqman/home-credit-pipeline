#!/usr/bin/env python3
"""Reset the SIM lab to clean baseline — re-seed + re-build sim only. Never hand-patched.

Usage: python simulation/faults/reset.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SIM = ROOT / "simulation"


def main() -> int:
    print("[reset] this is a stub until simulation/sim_dbt/ has real seeds + a build target.")
    print("[reset] intended sequence: regenerate sim synthetic data -> dbt seed --target sim "
          "-> dbt build --target sim -> python simulation/check_isolation.py")
    result = subprocess.run([sys.executable, str(SIM / "check_isolation.py")])
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
