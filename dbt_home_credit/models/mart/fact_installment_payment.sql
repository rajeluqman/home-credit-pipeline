-- Grain: 1 row = 1 installment payment (SK_ID_PREV + NUM_INSTALMENT_NUMBER).
-- days_payment_diff from int_installment_payments: positive = late, negative = early.

SELECT
    {{ generate_surrogate_key(['sk_id_prev', 'num_instalment_number']) }}   AS payment_sk,
    sk_id_curr,
    sk_id_prev,
    num_instalment_number,
    days_instalment,
    days_entry_payment,
    amt_instalment,
    amt_payment,
    days_payment_diff,
    ingestion_date
FROM {{ ref('int_installment_payments') }}
