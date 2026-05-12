-- Source: silver_bureau

SELECT
    SK_ID_CURR::INTEGER         AS sk_id_curr,
    SK_ID_BUREAU::INTEGER       AS sk_id_bureau,
    CREDIT_ACTIVE::VARCHAR      AS credit_active,
    CREDIT_CURRENCY::VARCHAR    AS credit_currency,
    DAYS_CREDIT::INTEGER        AS days_credit,
    CREDIT_DAY_OVERDUE::INTEGER AS credit_day_overdue,
    DAYS_CREDIT_ENDDATE::FLOAT  AS days_credit_enddate,
    DAYS_CREDIT_UPDATE::INTEGER AS days_credit_update,
    AMT_CREDIT_SUM::FLOAT       AS amt_credit_sum,
    AMT_CREDIT_SUM_DEBT::FLOAT  AS amt_credit_sum_debt,
    AMT_CREDIT_SUM_LIMIT::FLOAT AS amt_credit_sum_limit,
    AMT_CREDIT_SUM_OVERDUE::FLOAT AS amt_credit_sum_overdue,
    CREDIT_TYPE::VARCHAR        AS credit_type,
    CNT_CREDIT_PROLONG::INTEGER AS cnt_credit_prolong,
    ingestion_date::DATE        AS ingestion_date
FROM {{ source('silver', 'silver_bureau') }}
WHERE SK_ID_BUREAU IS NOT NULL
