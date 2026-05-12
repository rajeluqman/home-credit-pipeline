# ADR-001: Data Modelling Paradigm — Kimball Star Schema

Status: Accepted
Date  : 2026-05-12
Owner : Data Architect + Data Platform Engineer

## Context
Home Credit dataset: 7 CSV files, 300k+ applicants, analytics use case.

## Decision
Paradigm: Kimball — Star Schema

## Consequences
(+) Standard analytics pattern — joins manageable dalam AWS Glue
(+) Snowflake query cost predictable
(+) SCD Type 2 directly proves resume bullet point
(-) More joins vs OBT
(-) bureau_balance (27M rows) needs careful partitioning

## Alternatives Rejected
OBT: rejected — bureau_balance 27M rows + installments 13M rows
     nested Array/Struct = memory risk + Snowflake cost unpredictable
