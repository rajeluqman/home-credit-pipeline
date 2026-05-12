-- Source: silver_bureau_balance (1 row per SK_ID_BUREAU — MONTHS_BALANCE=0)

SELECT
    SK_ID_BUREAU::INTEGER   AS sk_id_bureau,
    STATUS::VARCHAR         AS status,
    ingestion_date::DATE    AS ingestion_date
FROM {{ source('silver', 'silver_bureau_balance') }}
WHERE SK_ID_BUREAU IS NOT NULL
