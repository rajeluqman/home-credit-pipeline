-- FK integrity: every fact_bureau_credit.applicant_sk must resolve in dim_applicant.

SELECT f.sk_id_bureau, f.applicant_sk
FROM {{ ref('fact_bureau_credit') }} f
LEFT JOIN {{ ref('dim_applicant') }} d ON f.applicant_sk = d.applicant_sk
WHERE d.applicant_sk IS NULL
  AND f.applicant_sk IS NOT NULL
