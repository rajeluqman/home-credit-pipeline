-- Select tracked SCD2 columns + PII masked columns from stg_application.
-- This is the snapshot source — only columns that snap_applicant tracks.

SELECT
    sk_id_curr          AS applicant_id,
    name_income_type,
    name_education_type,
    name_family_status,
    cnt_children,
    days_birth_masked,
    days_employed_masked,
    ingestion_date
FROM {{ ref('stg_application') }}
