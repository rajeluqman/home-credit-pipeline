-- Grain: 1 row = 1 loan application (SK_ID_CURR).
-- KPI-04: income_to_credit_ratio = AMT_INCOME_TOTAL / NULLIF(AMT_CREDIT, 0)

SELECT
    {{ generate_surrogate_key(['sk_id_curr']) }}     AS loan_application_sk,
    d.applicant_sk,
    lt.loan_type_id,
    a.sk_id_curr,
    a.target_flag,
    a.amt_credit,
    a.amt_annuity,
    a.amt_income_total,
    a.amt_income_total / NULLIF(a.amt_credit, 0)    AS income_to_credit_ratio,
    a.ingestion_date
FROM {{ ref('stg_application') }} a
LEFT JOIN {{ ref('dim_applicant') }} d
    ON a.sk_id_curr = d.applicant_id AND d.is_current = TRUE
LEFT JOIN {{ ref('dim_loan_type') }} lt
    ON a.name_contract_type = lt.loan_type_name
