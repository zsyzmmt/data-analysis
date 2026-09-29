# -*- coding: utf-8 -*-
"""
Step 2: SQL 分析
读取 data/cleaned/ 清洗数据 -> 按 sql/01_建表DDL.sql 建库导入 SQLite
-> 依次执行 02/03/04 分析 SQL -> 每条 @QUERY 结果导出 output/tables/*.csv
"""
import os
import re
import sqlite3
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN = os.path.join(BASE, "data", "cleaned")
SQLDIR = os.path.join(BASE, "sql")
OUT = os.path.join(BASE, "output", "tables")
os.makedirs(OUT, exist_ok=True)
DB = os.path.join(BASE, "data", "analysis.db")

conn = sqlite3.connect(DB)
cur = conn.cursor()

# ---------- 1. 建表 ----------
ddl = open(os.path.join(SQLDIR, "01_建表DDL.sql"), encoding="utf-8").read()
cur.executescript(ddl)
print("[DDL] 建表完成")

# ---------- 2. 导入清洗数据 ----------
def load_table(csv_gz, table, cols=None):
    df = pd.read_csv(os.path.join(CLEAN, csv_gz))
    if cols:
        df = df[cols]
    df.to_sql(table, conn, if_exists="append", index=False, method="multi", chunksize=40)
    print(f"[导入] {table}: {len(df)} 行")

load_table("taobao_behavior_cleaned.csv.gz", "taobao_behavior")

ab = pd.read_csv(os.path.join(CLEAN, "airbnb_listings_cleaned.csv.gz"))
ab = ab.rename(columns={"neighbourhood_cleansed": "neighbourhood"})
ab = ab[["id", "host_id", "host_name", "host_is_superhost", "host_listings_count",
         "host_scale", "neighbourhood", "room_type", "property_type", "accommodates",
         "bedrooms", "beds", "price", "price_winsor", "minimum_nights", "number_of_reviews",
         "number_of_reviews_ltm", "review_scores_rating", "availability_365",
         "estimated_revenue_l365d", "occupancy_ratio"]]
ab.to_sql("airbnb_listings", conn, if_exists="append", index=False, method="multi", chunksize=40)
print(f"[导入] airbnb_listings: {len(ab)} 行")
load_table("airbnb_reviews_cleaned.csv.gz", "airbnb_reviews")
yp = pd.read_csv(os.path.join(CLEAN, "yelp_reviews_cleaned.csv.gz"))
yp = yp.rename(columns={"Date": "review_date", "Rating": "rating"})
yp = yp[["business_id", "business_name", "review_date", "rating", "review_len",
         "word_count", "elite_flag", "sentiment", "sentiment_label"]]
yp.to_sql("yelp_reviews", conn, if_exists="append", index=False, method="multi", chunksize=40)
print(f"[导入] yelp_reviews: {len(yp)} 行")
load_table("reddit_chatgpt_cleaned.csv.gz", "reddit_chatgpt")
conn.commit()

# ---------- 3. 执行分析 SQL 并导出 ----------
QUERY_MARK = re.compile(r"^--\s*@QUERY:\s*(\S+)", re.M)
executed = []

for sqlfile in ["02_淘宝用户行为分析.sql", "03_香港Airbnb供给定价分析.sql", "04_Yelp与Reddit舆情分析.sql"]:
    text = open(os.path.join(SQLDIR, sqlfile), encoding="utf-8").read()
    # 按行首的 @QUERY 标记切分
    parts = re.split(r"(?m)(?=^--\s*@QUERY:)", text)
    for part in parts:
        m = QUERY_MARK.search(part)
        if not m:
            continue
        name = m.group(1)
        sql = "\n".join(l for l in part.splitlines() if not l.strip().startswith("--")).strip()
        if not sql:
            continue
        try:
            df = pd.read_sql_query(sql, conn)
            df.to_csv(os.path.join(OUT, f"{name}.csv"), index=False, encoding="utf-8-sig")
            executed.append((sqlfile, name, len(df)))
            print(f"[分析] {name}: {len(df)} 行 x {len(df.columns)} 列")
        except Exception as e:
            print(f"[错误] {name}: {e}")
            raise

conn.close()
print(f"\n=== SQL 分析完成, 共执行 {len(executed)} 条查询 ===")
