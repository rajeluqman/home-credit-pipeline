-- SCD Type 1 — static lookup from distinct contract types in silver_application.
-- Expected 2 rows: 'Cash loans', 'Revolving loans'.

{{
  config(materialized='table')
}}

SELECT DISTINCT
    {{ generate_surrogate_key(['name_contract_type']) }}    AS loan_type_id,
    name_contract_type                                      AS loan_type_name,
    current_timestamp()                                     AS dbt_updated_at
FROM {{ ref('stg_application') }}
WHERE name_contract_type IS NOT NULL
