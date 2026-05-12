-- FK integrity: every fact_loan_application.applicant_sk must resolve in dim_applicant.
-- Returns rows that are orphaned (no matching applicant_sk in dim_applicant).

SELECT f.sk_id_curr, f.applicant_sk
FROM {{ ref('fact_loan_application') }} f
LEFT JOIN {{ ref('dim_applicant') }} d ON f.applicant_sk = d.applicant_sk
WHERE d.applicant_sk IS NULL
  AND f.applicant_sk IS NOT NULL
