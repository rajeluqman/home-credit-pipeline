-- Source: silver_application (Snowflake Silver schema)
-- Cast types, rename to snake_case, no business logic.

SELECT
    SK_ID_CURR::INTEGER             AS sk_id_curr,
    TARGET::INTEGER                 AS target_flag,
    NAME_CONTRACT_TYPE::VARCHAR     AS name_contract_type,
    AMT_CREDIT::FLOAT               AS amt_credit,
    AMT_ANNUITY::FLOAT              AS amt_annuity,
    AMT_INCOME_TOTAL::FLOAT         AS amt_income_total,
    AMT_GOODS_PRICE::FLOAT          AS amt_goods_price,
    NAME_INCOME_TYPE::VARCHAR       AS name_income_type,
    NAME_EDUCATION_TYPE::VARCHAR    AS name_education_type,
    NAME_FAMILY_STATUS::VARCHAR     AS name_family_status,
    NAME_HOUSING_TYPE::VARCHAR      AS name_housing_type,
    CNT_CHILDREN::INTEGER           AS cnt_children,
    FLAG_OWN_CAR::VARCHAR           AS flag_own_car,
    FLAG_OWN_REALTY::VARCHAR        AS flag_own_realty,
    OCCUPATION_TYPE::VARCHAR        AS occupation_type,
    ORGANIZATION_TYPE::VARCHAR      AS organization_type,
    REGION_RATING_CLIENT::INTEGER   AS region_rating_client,
    EXT_SOURCE_1::FLOAT             AS ext_source_1,
    EXT_SOURCE_2::FLOAT             AS ext_source_2,
    EXT_SOURCE_3::FLOAT             AS ext_source_3,
    DAYS_BIRTH_MASKED::VARCHAR      AS days_birth_masked,
    DAYS_EMPLOYED_MASKED::VARCHAR   AS days_employed_masked,
    ingestion_date::DATE            AS ingestion_date
FROM {{ source('silver', 'silver_application') }}
WHERE SK_ID_CURR IS NOT NULL
