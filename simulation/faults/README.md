# Fault Catalog — Home Credit Simulation Lab

Named, reversible faults for troubleshooting drills. `inject.py <fault_id>` applies one;
`reset.py` rebuilds clean sim state from sim seeds (never hand-patched).

| ID | Fault | Mirrors a real risk from |
|---|---|---|
| F01 | PII mask order reversed (SHA-256 before sentinel-null) | ADR-002 |
| F02 | SCD2 snapshot `strategy` swapped to `timestamp` (breaks `is_current` semantics) | ADR-001, `tests/identity_contract.py` ID1 |
| F03 | Glue MERGE key dropped → duplicate rows on re-run | M3 (CURRICULUM.md) |
| F04 | bureau_balance OOM simulated (oversized synthetic fan-out) | ADR-003 |

Catalog entries (full repro steps) live in `simulation/faults/catalog/`.
