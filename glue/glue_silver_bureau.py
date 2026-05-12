"""
AWS Glue 4.0 — Silver Bureau + Bureau Balance Transform
G.1X × 2 workers (fallback G.2X if OOM on bureau_balance 27M rows)

Sources:
  s3://{bucket}/bronze/bureau/ingestion_date={date}/
  s3://{bucket}/bronze/bureau_balance/ingestion_date={date}/

Targets:
  s3://{bucket}/silver/silver_bureau/ingestion_date={date}/
  s3://{bucket}/silver/silver_bureau_balance/ingestion_date={date}/

Note: Depends on silver_application completing first (RI GX check).
"""

import sys
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from delta.tables import DeltaTable

args = getResolvedOptions(sys.argv, ["JOB_NAME", "env", "date", "bucket"])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

BUCKET = args["bucket"]
DATE = args["date"]

SRC_BUREAU = f"s3://{BUCKET}/bronze/bureau/ingestion_date={DATE}/"
SRC_BB = f"s3://{BUCKET}/bronze/bureau_balance/ingestion_date={DATE}/"
TGT_BUREAU = f"s3://{BUCKET}/silver/silver_bureau/ingestion_date={DATE}/"
TGT_BB = f"s3://{BUCKET}/silver/silver_bureau_balance/ingestion_date={DATE}/"

BUREAU_COLS = [
    "SK_ID_CURR", "SK_ID_BUREAU", "CREDIT_ACTIVE", "CREDIT_CURRENCY",
    "DAYS_CREDIT", "CREDIT_DAY_OVERDUE", "DAYS_CREDIT_ENDDATE",
    "DAYS_CREDIT_UPDATE", "AMT_CREDIT_SUM", "AMT_CREDIT_SUM_DEBT",
    "AMT_CREDIT_SUM_LIMIT", "AMT_CREDIT_SUM_OVERDUE", "CREDIT_TYPE",
    "CNT_CREDIT_PROLONG", "ingestion_ts", "ingestion_date",
]

# ── Bureau ────────────────────────────────────────────────────────────────────
df_bureau = spark.read.format("delta").load(SRC_BUREAU)
existing = [c for c in BUREAU_COLS if c in df_bureau.columns]
df_bureau = df_bureau.select(existing)

w = Window.partitionBy("SK_ID_BUREAU").orderBy(F.col("ingestion_ts").desc())
df_bureau = (
    df_bureau.withColumn("_rank", F.row_number().over(w))
    .filter(F.col("_rank") == 1)
    .drop("_rank")
)

if DeltaTable.isDeltaTable(spark, TGT_BUREAU):
    dt = DeltaTable.forPath(spark, TGT_BUREAU)
    dt.alias("t").merge(
        df_bureau.alias("s"), "t.SK_ID_BUREAU = s.SK_ID_BUREAU"
    ).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()
else:
    df_bureau.write.format("delta").mode("overwrite").partitionBy("ingestion_date").save(TGT_BUREAU)

# ── Bureau Balance ────────────────────────────────────────────────────────────
# Filter MONTHS_BALANCE=0 → 1 row per SK_ID_BUREAU
df_bb = spark.read.format("delta").load(SRC_BB)
df_bb = df_bb.filter(F.col("MONTHS_BALANCE") == 0)
df_bb = df_bb.select("SK_ID_BUREAU", "STATUS", "ingestion_ts", "ingestion_date")
df_bb = (
    df_bb.withColumn("_rank", F.row_number().over(
        Window.partitionBy("SK_ID_BUREAU").orderBy(F.col("ingestion_ts").desc())
    ))
    .filter(F.col("_rank") == 1)
    .drop("_rank")
)

if DeltaTable.isDeltaTable(spark, TGT_BB):
    dt = DeltaTable.forPath(spark, TGT_BB)
    dt.alias("t").merge(
        df_bb.alias("s"), "t.SK_ID_BUREAU = s.SK_ID_BUREAU"
    ).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()
else:
    df_bb.write.format("delta").mode("overwrite").partitionBy("ingestion_date").save(TGT_BB)

job.commit()
