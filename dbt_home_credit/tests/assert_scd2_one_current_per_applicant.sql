-- SCD2 invariant: exactly 1 is_current=TRUE per applicant_id.
-- Fails if any applicant_id has 0 or 2+ current records.

SELECT applicant_id, COUNT(*) AS current_count
FROM {{ ref('dim_applicant') }}
WHERE is_current = TRUE
GROUP BY applicant_id
HAVING COUNT(*) != 1
