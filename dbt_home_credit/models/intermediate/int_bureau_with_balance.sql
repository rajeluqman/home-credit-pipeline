-- Join silver_bureau + silver_bureau_balance.
-- 1 row per sk_id_bureau with bureau_balance_status (STATUS at MONTHS_BALANCE=0).

SELECT
    b.sk_id_curr,
    b.sk_id_bureau,
    b.credit_active,
    b.credit_currency,
    b.days_credit,
    b.credit_day_overdue,
    b.days_credit_enddate,
    b.days_credit_update,
    b.amt_credit_sum,
    b.amt_credit_sum_debt,
    b.amt_credit_sum_limit,
    b.amt_credit_sum_overdue,
    b.credit_type,
    b.cnt_credit_prolong,
    bb.status AS bureau_balance_status,
    b.ingestion_date
FROM {{ ref('stg_bureau') }} b
LEFT JOIN {{ ref('stg_bureau_balance') }} bb
    ON b.sk_id_bureau = bb.sk_id_bureau
