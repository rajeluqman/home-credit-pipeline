#!/usr/bin/env python3
"""Isolation guard for the Home Credit simulation lab (simulation/).

Ported from creative_intelligence_lab's simulation/check_isolation.py (pipeline-retrofit
effort). Proves the sim lab cannot touch the real Glue/dbt/Snowflake pipeline, so fault-
injection / optimization drills can never corrupt canonical data or models. Deterministic,
no AWS/Snowflake connection. Run before every sim session AND before committing sim work:

    python simulation/check_isolation.py

Exit 0 = isolated (safe to break things). Exit 1 = a boundary was crossed (STOP). Enforces
R1/R2/R3 of ISOLATION_CONTRACT.md; R4/R5 stay partly human.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIM = ROOT / "simulation"
REAL_DBT = ROOT / "dbt_home_credit" / "dbt_project.yml"
SIM_DBT = SIM / "sim_dbt" / "dbt_project.yml"
SIM_PREFIX = "/sim/"


def project_name(p: Path) -> str | None:
    if not p.exists():
        return None
    m = re.search(r"^\s*name:\s*['\"]?([\w-]+)", p.read_text(errors="ignore"), re.M)
    return m.group(1) if m else None


def main() -> int:
    failures: list[str] = []
    notes: list[str] = []

    # R2 — sim dbt project name must differ from the real one.
    real_name = project_name(REAL_DBT)
    sim_name = project_name(SIM_DBT)
    if sim_name is None:
        notes.append("R2: simulation/sim_dbt/dbt_project.yml not present yet — name check skipped")
    elif real_name and sim_name == real_name:
        failures.append(f"R2: sim dbt project name '{sim_name}' equals real '{real_name}' — must differ")

    # R3 — no sim SQL may ref() a real model.
    real_models = {p.stem for p in (ROOT / "dbt_home_credit" / "models").rglob("*.sql")} \
        if (ROOT / "dbt_home_credit" / "models").exists() else set()
    for f in SIM.rglob("*.sql"):
        text = f.read_text(errors="ignore")
        for m in re.findall(r"\bref\(\s*['\"]([a-zA-Z0-9_]+)['\"]", text):
            if m in real_models:
                failures.append(f"R3: {f.relative_to(ROOT)} ref()s real model '{m}' — cross-project contamination")

    # R1 — every s3:// literal in a sim file must contain /sim/. This script's own source
    # (which defines the s3:// regex pattern as a string literal) is excluded — it's tooling,
    # not a path declaration.
    skip = {Path(__file__).resolve()}
    for f in SIM.rglob("*"):
        if not f.is_file() or f.suffix not in (".sql", ".md", ".yml", ".yaml") or f.resolve() in skip:
            continue
        for lineno, line in enumerate(f.read_text(errors="ignore").splitlines(), 1):
            for uri in re.findall(r"s3://[^\s'\"`]+", line):
                if SIM_PREFIX not in uri:
                    failures.append(f"R1: {f.relative_to(ROOT)}:{lineno}: s3:// path missing '/sim/': {uri}")

    for n in notes:
        print(f"ℹ️  {n}")

    if failures:
        print(f"\n❌ ISOLATION CONTRACT FAILED — {len(failures)} violation(s):", file=sys.stderr)
        for fail in failures:
            print(f"   • {fail}", file=sys.stderr)
        return 1
    print("✅ isolation contract OK — sim lab cannot touch the real pipeline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
