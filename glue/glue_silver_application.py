"""
AWS Glue 4.0 — Silver Application Transform
G.1X × 2 workers | Python 3 | Glue version 4.0

Source : s3://{bucket}/bronze/application_train/ingestion_date={date}/
Target : s3://{bucket}/silver/silver_application/ingestion_date={date}/

Transforms (PIPELINE_SPEC order):
  1. Column subset (23 cols)
  2. DI-001: ORGANIZATION_TYPE XNA → NULL
  3. DI-002: DAYS_EMPLOYED 365243 → NULL
  4. PII mask DAYS_EMPLOYED (SHA-256 after null substitution)
  5. PII mask DAYS_BIRTH (SHA-256, always)
  6. Drop raw PII columns
  7. Dedup on SK_ID_CURR (max ingestion_ts)
  8. Delta MERGE (UPSERT on SK_ID_CURR)
"""

import sys
import hashlib
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import functions as F
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType
from delta.tables import DeltaTable

args = getResolvedOptions(sys.argv, ["JOB_NAME", "env", "date", "bucket"])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

ENV = args["env"]
DATE = args["date"]
BUCKET = args["bucket"]

SOURCE = f"s3://{BUCKET}/bronze/application_train/ingestion_date={DATE}/"
TARGET = f"s3://{BUCKET}/silver/silver_application/ingestion_date={DATE}/"

KEEP_COLS = [
    "SK_ID_CURR", "TARGET", "NAME_CONTRACT_TYPE", "AMT_CREDIT", "AMT_ANNUITY",
    "AMT_INCOME_TOTAL", "AMT_GOODS_PRICE", "NAME_INCOME_TYPE", "NAME_EDUCATION_TYPE",
    "NAME_FAMILY_STATUS", "NAME_HOUSING_TYPE", "DAYS_BIRTH", "DAYS_EMPLOYED",
    "FLAG_OWN_CAR", "FLAG_OWN_REALTY", "CNT_CHILDREN", "OCCUPATION_TYPE",
    "ORGANIZATION_TYPE", "REGION_RATING_CLIENT", "EXT_SOURCE_1", "EXT_SOURCE_2",
    "EXT_SOURCE_3", "ingestion_ts", "ingestion_date",
]


@udf(returnType=StringType())
def sha256_udf(value):
    if value is None:
        return None
    return hashlib.sha256(str(value).encode()).hexdigest()


df = spark.read.format("delta").load(SOURCE)

# Step 1: Column subset
existing = [c for c in KEEP_COLS if c in df.columns]
df = df.select(existing)

# Step 2: DI-001 XNA → NULL
df = df.withColumn(
    "ORGANIZATION_TYPE",
    F.when(F.col("ORGANIZATION_TYPE") == "XNA", None).otherwise(F.col("ORGANIZATION_TYPE"))
)

# Step 3: DI-002 365243 → NULL
df = df.withColumn(
    "DAYS_EMPLOYED_CLEAN",
    F.when(F.col("DAYS_EMPLOYED") == 365243, None).otherwise(F.col("DAYS_EMPLOYED"))
)

# Step 4: PII mask DAYS_EMPLOYED
df = df.withColumn("DAYS_EMPLOYED_MASKED", sha256_udf(F.col("DAYS_EMPLOYED_CLEAN").cast("string")))

# Step 5: PII mask DAYS_BIRTH
df = df.withColumn("DAYS_BIRTH_MASKED", sha256_udf(F.col("DAYS_BIRTH").cast("string")))

# Step 6: Drop raw PII
df = df.drop("DAYS_BIRTH", "DAYS_EMPLOYED", "DAYS_EMPLOYED_CLEAN")

# Step 7: Dedup — keep latest per SK_ID_CURR
from pyspark.sql.window import Window
w = Window.partitionBy("SK_ID_CURR").orderBy(F.col("ingestion_ts").desc())
df = df.withColumn("_rank", F.row_number().over(w)).filter(F.col("_rank") == 1).drop("_rank")

# Step 8: Delta MERGE (UPSERT)
if DeltaTable.isDeltaTable(spark, TARGET):
    dt = DeltaTable.forPath(spark, TARGET)
    dt.alias("t").merge(
        df.alias("s"),
        "t.SK_ID_CURR = s.SK_ID_CURR"
    ).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()
else:
    df.write.format("delta").mode("overwrite").partitionBy("ingestion_date").save(TARGET)

job.commit()
