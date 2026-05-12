# BRD: Home Credit Risk Pipeline
> Status: DRAFT — Pending Phase 1 sign-off
> Domain: Banking | Dataset: Home Credit Default Risk

## Stakeholders
| Stakeholder | Role | Data Need |
|-------------|------|-----------|
| Risk Team | Primary consumer | Default rate by segment |
| Compliance | Audit | PII masking evidence, SCD audit trail |
| Portfolio Mgmt | Secondary | Loan portfolio health KPIs |

## Business Requirements
1. Ingest 300k+ credit records dari 7 source tables
2. Mask PII/quasi-identifiers (SHA-256) sebelum analytics layer
3. Track applicant history via SCD Type 2
4. Surface credit risk KPIs dalam Gold layer

## KPIs
| KPI | Formula | Frequency |
|-----|---------|-----------|
| Default Rate | COUNT(TARGET=1) / COUNT(*) | Daily |
| Avg Credit Amount | AVG(AMT_CREDIT) per loan_type | Daily |
| Bureau Delinquency Rate | Bureau bad / total bureau records | Daily |

## Sign-off Gate
| Agent | Status |
|-------|--------|
| BA | PENDING |
| PO | PENDING |
| PM | PENDING |
| DQS | PENDING |
