"""
AWS Glue 4.0 — Silver POS Cash + Credit Card Balance Transform
G.1X × 2 workers

Sources:
  s3://{bucket}/bronze/POS_CASH_balance/ingestion_date={date}/
  s3://{bucket}/bronze/credit_card_balance/ingestion_date={date}/

Targets:
  s3://{bucket}/silver/silver_pos_cash/ingestion_date={date}/
  s3://{bucket}/silver/silver_credit_card/ingestion_date={date}/

No natural dedup key → append mode with ingestion_date partition.
Gold integration deferred (BR-11 credit_card, BR-12 POS_CASH).
"""

import sys
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import functions as F

args = getResolvedOptions(sys.argv, ["JOB_NAME", "env", "date", "bucket"])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

BUCKET = args["bucket"]
DATE = args["date"]

SRC_POS = f"s3://{BUCKET}/bronze/POS_CASH_balance/ingestion_date={DATE}/"
SRC_CC = f"s3://{BUCKET}/bronze/credit_card_balance/ingestion_date={DATE}/"
TGT_POS = f"s3://{BUCKET}/silver/silver_pos_cash/ingestion_date={DATE}/"
TGT_CC = f"s3://{BUCKET}/silver/silver_credit_card/ingestion_date={DATE}/"

POS_COLS = [
    "SK_ID_PREV", "SK_ID_CURR", "MONTHS_BALANCE", "CNT_INSTALMENT",
    "CNT_INSTALMENT_FUTURE", "NAME_CONTRACT_STATUS", "SK_DPD", "SK_DPD_DEF",
    "ingestion_ts", "ingestion_date",
]

CC_COLS = [
    "SK_ID_PREV", "SK_ID_CURR", "MONTHS_BALANCE", "AMT_BALANCE",
    "AMT_CREDIT_LIMIT_ACTUAL", "AMT_DRAWINGS_CURRENT", "AMT_PAYMENT_CURRENT",
    "SK_DPD", "NAME_CONTRACT_STATUS", "ingestion_ts", "ingestion_date",
]

# POS Cash
df_pos = spark.read.format("delta").load(SRC_POS)
existing_pos = [c for c in POS_COLS if c in df_pos.columns]
df_pos = df_pos.select(existing_pos)
df_pos.write.format("delta").mode("overwrite").partitionBy("ingestion_date").save(TGT_POS)

# Credit Card
df_cc = spark.read.format("delta").load(SRC_CC)
existing_cc = [c for c in CC_COLS if c in df_cc.columns]
df_cc = df_cc.select(existing_cc)
df_cc.write.format("delta").mode("overwrite").partitionBy("ingestion_date").save(TGT_CC)

job.commit()
