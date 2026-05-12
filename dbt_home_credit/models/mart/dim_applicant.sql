-- SCD Type 2 dimension — aliases snap_applicant dbt columns to resume-aligned names.
-- start_date, end_date, is_current prove SCD2 implementation in portfolio.

SELECT
    {{ generate_surrogate_key(['applicant_id', 'dbt_valid_from']) }} AS applicant_sk,
    applicant_id,
    name_income_type,
    name_education_type,
    name_family_status,
    cnt_children,
    days_birth_masked,
    days_employed_masked,
    dbt_valid_from::DATE                                        AS start_date,
    dbt_valid_to::DATE                                          AS end_date,
    CASE WHEN dbt_valid_to IS NULL THEN TRUE ELSE FALSE END     AS is_current
FROM {{ ref('snap_applicant') }}
