-- SCD Type 1 — static mapping for CREDIT_ACTIVE values from silver_bureau.
-- 4 known status codes: Active, Closed, Bad debt, Sold.

{{
  config(materialized='table')
}}

SELECT
    {{ generate_surrogate_key(['status_code']) }}   AS status_id,
    status_code,
    status_description,
    current_timestamp()                             AS dbt_updated_at
FROM (
    VALUES
        ('Active',   'Active bureau credit line'),
        ('Closed',   'Closed bureau credit line'),
        ('Bad debt', 'Bureau credit in bad debt status'),
        ('Sold',     'Bureau credit sold to third party')
) AS t(status_code, status_description)
