-- Grain: 1 row = 1 bureau credit record (SK_ID_BUREAU).
-- KPI-03 source: credit_day_overdue.

SELECT
    {{ generate_surrogate_key(['sk_id_bureau']) }}   AS bureau_credit_sk,
    d.applicant_sk,
    b.sk_id_curr,
    b.sk_id_bureau,
    cs.status_id                                     AS credit_status_id,
    b.credit_day_overdue,
    b.amt_credit_sum,
    b.amt_credit_sum_debt,
    b.credit_type,
    b.bureau_balance_status,
    b.ingestion_date
FROM {{ ref('int_bureau_with_balance') }} b
LEFT JOIN {{ ref('dim_applicant') }} d
    ON b.sk_id_curr = d.applicant_id AND d.is_current = TRUE
LEFT JOIN {{ ref('dim_credit_status') }} cs
    ON b.credit_active = cs.status_code
