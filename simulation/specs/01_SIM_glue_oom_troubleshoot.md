# SIM Spec — Glue OOM Troubleshoot Drill

> Isolation-contracted (ISOLATION_CONTRACT.md R1-R5). Run on a `drill/*` branch.

## Scenario
Inject F04 (`simulation/faults/inject.py F04`) — an oversized synthetic fan-out simulating the
27M-row `bureau_balance` join risk sized in `docs/ADR/ADR-003-kimball-over-obt-sizing.md`.

## Pedagogy
Troubleshooting mode (CIL CURRICULUM convention): hypothesis-log BEFORE running anything.
1. Write `hypothesis → test → predicted output` before touching the sim.
2. Observe (sim Glue job logs / dbt run output against `HOME_CREDIT_RISK_SIM` schema).
3. Root-cause: tie back to the ADR-003 sizing math — was the prediction right?
4. Fix in the sim only; `faults/reset.py` to return to clean baseline.

## Acceptance
Owner can explain, unaided, why Kimball (not OBT) avoids this failure mode — the C-P-I-D-I-R
interview-drill format from CIL's EXECUTIVE_STORYTELLING_TEMPLATE, ported on request if the
owner wants to extend this spec set.
