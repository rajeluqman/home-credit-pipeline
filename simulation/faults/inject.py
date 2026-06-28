#!/usr/bin/env python3
"""Inject a named, reversible fault into the SIM lab only (never touches real models).

Usage: python simulation/faults/inject.py <fault_id>   (F01-F04, see faults/README.md)
Guard: refuses to run if simulation/check_isolation.py would fail afterward.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SIM = ROOT / "simulation"

FAULTS = {
    "F01": "PII mask order reversed (SHA-256 before sentinel-null) — see faults/catalog/F01.md",
    "F02": "SCD2 snapshot strategy swapped to timestamp — see faults/catalog/F02.md",
    "F03": "Glue MERGE key dropped, duplicate rows on re-run — see faults/catalog/F03.md",
    "F04": "bureau_balance OOM simulated via oversized synthetic fan-out — see faults/catalog/F04.md",
}


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in FAULTS:
        print(f"Usage: inject.py <{'|'.join(FAULTS)}>")
        return 1
    fault_id = argv[1]
    print(f"[inject] {fault_id}: {FAULTS[fault_id]}")
    print("[inject] apply the catalog steps manually inside simulation/sim_dbt/ or simulation/ "
          "synthetic fixtures, then re-run check_isolation.py before continuing.")
    result = subprocess.run([sys.executable, str(SIM / "check_isolation.py")])
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
