"""
AWS Glue 4.0 — Silver Installments Payments Transform
G.1X × 2 workers

Source : s3://{bucket}/bronze/installments_payments/ingestion_date={date}/
Target : s3://{bucket}/silver/silver_installments/ingestion_date={date}/

No PII masking. Dedup on (SK_ID_PREV, NUM_INSTALMENT_NUMBER).
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
SOURCE = f"s3://{BUCKET}/bronze/installments_payments/ingestion_date={DATE}/"
TARGET = f"s3://{BUCKET}/silver/silver_installments/ingestion_date={DATE}/"

KEEP_COLS = [
    "SK_ID_PREV", "SK_ID_CURR", "NUM_INSTALMENT_VERSION", "NUM_INSTALMENT_NUMBER",
    "DAYS_INSTALMENT", "DAYS_ENTRY_PAYMENT", "AMT_INSTALMENT", "AMT_PAYMENT",
    "ingestion_ts", "ingestion_date",
]

df = spark.read.format("delta").load(SOURCE)
existing = [c for c in KEEP_COLS if c in df.columns]
df = df.select(existing)

w = Window.partitionBy("SK_ID_PREV", "NUM_INSTALMENT_NUMBER").orderBy(F.col("ingestion_ts").desc())
df = df.withColumn("_rank", F.row_number().over(w)).filter(F.col("_rank") == 1).drop("_rank")

if DeltaTable.isDeltaTable(spark, TARGET):
    dt = DeltaTable.forPath(spark, TARGET)
    dt.alias("t").merge(
        df.alias("s"),
        "t.SK_ID_PREV = s.SK_ID_PREV AND t.NUM_INSTALMENT_NUMBER = s.NUM_INSTALMENT_NUMBER"
    ).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()
else:
    df.write.format("delta").mode("overwrite").partitionBy("ingestion_date").save(TARGET)

job.commit()
