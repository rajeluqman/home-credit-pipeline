-- Source: silver_installments

SELECT
    SK_ID_PREV::INTEGER                 AS sk_id_prev,
    SK_ID_CURR::INTEGER                 AS sk_id_curr,
    NUM_INSTALMENT_VERSION::FLOAT       AS num_instalment_version,
    NUM_INSTALMENT_NUMBER::FLOAT        AS num_instalment_number,
    DAYS_INSTALMENT::FLOAT              AS days_instalment,
    DAYS_ENTRY_PAYMENT::FLOAT           AS days_entry_payment,
    AMT_INSTALMENT::FLOAT               AS amt_instalment,
    AMT_PAYMENT::FLOAT                  AS amt_payment,
    ingestion_date::DATE                AS ingestion_date
FROM {{ source('silver', 'silver_installments') }}
WHERE SK_ID_PREV IS NOT NULL
