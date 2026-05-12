"""
AWS Glue 4.0 — Silver Previous Application Transform
G.1X × 2 workers

Source : s3://{bucket}/bronze/previous_application/ingestion_date={date}/
Target : s3://{bucket}/silver/silver_previous_application/ingestion_date={date}/

No PII masking. No dedup (SK_ID_PREV unique per row). 8 columns kept.
Gold fact deferred (BR-10 Could Have).
"""

import sys
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import functions as F
from delta.tables import DeltaTable

args = getResolvedOptions(sys.argv, ["JOB_NAME", "env", "date", "bucket"])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

BUCKET = args["bucket"]
DATE = args["date"]
SOURCE = f"s3://{BUCKET}/bronze/previous_application/ingestion_date={DATE}/"
TARGET = f"s3://{BUCKET}/silver/silver_previous_application/ingestion_date={DATE}/"

KEEP_COLS = [
    "SK_ID_PREV", "SK_ID_CURR", "NAME_CONTRACT_TYPE", "AMT_CREDIT",
    "AMT_APPLICATION", "NAME_CONTRACT_STATUS", "DAYS_DECISION",
    "NAME_PRODUCT_TYPE", "ingestion_ts", "ingestion_date",
]

df = spark.read.format("delta").load(SOURCE)
existing = [c for c in KEEP_COLS if c in df.columns]
df = df.select(existing)

if DeltaTable.isDeltaTable(spark, TARGET):
    dt = DeltaTable.forPath(spark, TARGET)
    dt.alias("t").merge(
        df.alias("s"), "t.SK_ID_PREV = s.SK_ID_PREV"
    ).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()
else:
    df.write.format("delta").mode("overwrite").partitionBy("ingestion_date").save(TARGET)

job.commit()
