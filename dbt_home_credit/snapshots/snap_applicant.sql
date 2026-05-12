{% snapshot snap_applicant %}
  {{
    config(
      target_schema='home_credit_gold',
      unique_key='applicant_id',
      strategy='check',
      check_cols=['name_income_type', 'name_education_type', 'name_family_status', 'cnt_children'],
      invalidate_hard_deletes=false
    )
  }}

  SELECT
    applicant_id,
    name_income_type,
    name_education_type,
    name_family_status,
    cnt_children,
    days_birth_masked,
    days_employed_masked
  FROM {{ ref('int_applicant_attributes') }}

{% endsnapshot %}
