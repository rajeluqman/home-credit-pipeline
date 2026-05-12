-- Add derived column days_payment_diff.
-- Positive = paid late, negative = paid early.

SELECT
    sk_id_prev,
    sk_id_curr,
    num_instalment_version,
    num_instalment_number,
    days_instalment,
    days_entry_payment,
    amt_instalment,
    amt_payment,
    days_entry_payment - days_instalment AS days_payment_diff,
    ingestion_date
FROM {{ ref('stg_installments') }}
