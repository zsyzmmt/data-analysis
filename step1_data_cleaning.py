# -*- coding: utf-8 -*-
"""
Step 1: 多源数据清洗
输入: data/raw/ 下的四个原始数据集
输出: data/cleaned/ 下的清洗后数据 + output/cleaning_report.csv 清洗日志
清洗动作: 去重 / 缺失值 / 异常值 / 类型转换 / 格式标准化 / 文本情感打分
"""
import os
import json
import pandas as pd
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw")
CLEAN = os.path.join(BASE, "data", "cleaned")
OUT = os.path.join(BASE, "output")
os.makedirs(CLEAN, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

log = []  # 清洗日志: (数据集, 步骤, 说明, 剩余行数)


def add_log(dataset, step, desc, n):
    log.append({"数据集": dataset, "步骤": step, "清洗动作": desc, "剩余记录数": n})
    print(f"[{dataset}] {step} {desc} -> {n}")


# ============================================================
# 1. 淘宝用户行为数据（阿里天池 UserBehavior 样本）
# ============================================================
def clean_taobao():
    dataset = "淘宝用户行为(天池)"
    df = pd.read_csv(os.path.join(RAW, "UserBehavior.csv"),
                     names=["user_id", "item_id", "category_id", "behavior_type", "timestamp"],
                     dtype=str)
    n0 = len(df)
    add_log(dataset, "原始数据", f"共 {n0} 条用户行为记录", n0)

    # 0) 关键字段缺失处理（存在整行缺失/字段为空的脏数据）
    df = df.dropna(subset=["user_id", "item_id", "category_id", "behavior_type", "timestamp"])
    for c in ["user_id", "item_id", "category_id", "timestamp"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["user_id", "item_id", "category_id", "timestamp"])
    for c in ["user_id", "item_id", "category_id", "timestamp"]:
        df[c] = df[c].astype("int64")
    add_log(dataset, "缺失值处理", "剔除字段缺失/非数值的脏记录", len(df))

    # 1) 行为类型合法性校验（仅保留 pv/fav/cart/buy）
    valid_types = {"pv", "fav", "cart", "buy"}
    df = df[df["behavior_type"].isin(valid_types)]
    add_log(dataset, "异常值过滤", "剔除非法行为类型", len(df))

    # 2) 时间合法性：官方数据窗口 2017-11-25 ~ 2017-12-03（北京时间）
    ts_min, ts_max = 1511539200, 1512316799  # 2017-11-25 00:00 ~ 2017-12-03 23:59 (+08)
    df = df[(df["timestamp"] >= ts_min) & (df["timestamp"] <= ts_max)]
    add_log(dataset, "异常值过滤", "剔除官方时间窗口外的记录", len(df))

    # 3) 去重（同一用户对同一商品的同一行为在同一秒视为重复）
    before = len(df)
    df = df.drop_duplicates(subset=["user_id", "item_id", "behavior_type", "timestamp"])
    add_log(dataset, "去重", f"剔除完全重复记录 {before - len(df)} 条", len(df))

    # 4) 缺失值检查（本数据集无缺失，防御性处理）
    df = df.dropna()
    add_log(dataset, "缺失值处理", "剔除关键字段缺失记录", len(df))

    # 5) 特征衍生：日期 / 小时 / 星期（增长运营排期分析用）
    dt = pd.to_datetime(df["timestamp"], unit="s") + pd.Timedelta(hours=8)  # UTC -> 北京时间
    df["datetime"] = dt
    df["date"] = dt.dt.date.astype(str)
    df["hour"] = dt.dt.hour
    df["weekday"] = dt.dt.dayofweek + 1  # 1-7

    df = df[["user_id", "item_id", "category_id", "behavior_type", "datetime", "date", "hour", "weekday"]]
    df.to_csv(os.path.join(CLEAN, "taobao_behavior_cleaned.csv.gz"), index=False, compression="gzip")
    print(f"  时间范围: {df['date'].min()} ~ {df['date'].max()}, 用户数 {df['user_id'].nunique()}")
    return {
        "rows": int(len(df)), "users": int(df["user_id"].nunique()),
        "items": int(df["item_id"].nunique()), "categories": int(df["category_id"].nunique()),
        "date_min": str(df["date"].min()), "date_max": str(df["date"].max()),
    }


# ============================================================
# 2. 香港 Airbnb 房源与评论（Inside Airbnb）
# ============================================================
def clean_airbnb():
    dataset = "香港Airbnb(InsideAirbnb)"
    keep_cols = ["id", "host_id", "host_name", "host_is_superhost",
                "host_listings_count", "neighbourhood_cleansed", "latitude", "longitude",
                "property_type", "room_type", "accommodates", "bedrooms", "beds",
                "price", "minimum_nights", "number_of_reviews", "number_of_reviews_ltm",
                "review_scores_rating", "availability_365", "estimated_revenue_l365d",
                "first_review", "last_review", "instant_bookable"]
    df = pd.read_csv(os.path.join(RAW, "listings_detailed.csv.gz"), usecols=keep_cols, low_memory=False)
    n0 = len(df)
    add_log(dataset, "原始数据", f"共 {n0} 条香港房源", n0)

    # 1) 价格清洗: "$1,234.00" -> 数值
    df["price"] = (df["price"].astype(str)
                   .str.replace(r"[\$,]", "", regex=True)
                   .str.strip().astype(float))

    # 2) 异常值过滤: 剔除无价格/非正价格房源
    df = df[df["price"] > 0]
    add_log(dataset, "异常值过滤", "剔除价格缺失或<=0的房源", len(df))

    # 3) 极端价格缩尾（99分位封顶，避免长尾拉偏均值; 同时保留 raw price 供分组）
    p99 = df["price"].quantile(0.99)
    df["price_winsor"] = df["price"].clip(upper=p99)
    add_log(dataset, "极端值缩尾", f"价格99分位=${p99:.0f} 以上封顶处理", len(df))

    # 4) 关键字段缺失处理
    for col, fill in [("bedrooms", np.nan), ("beds", np.nan),
                      ("review_scores_rating", np.nan)]:
        pass  # 保留 NaN，SQL 聚合时用 WHERE 过滤
    df = df.dropna(subset=["neighbourhood_cleansed", "room_type", "host_id"])
    add_log(dataset, "缺失值处理", "剔除区域/房型/房东缺失的房源", len(df))

    # 5) 供给饱和度衍生指标: 365天可订天数占比
    df["occupancy_ratio"] = (1 - df["availability_365"] / 365).round(4)

    # 6) 房东规模分层: 个人房东(<=2) / 小型(3-10) / 专业(11-50) / 机构(>50)
    df["host_listings_count"] = pd.to_numeric(df["host_listings_count"], errors="coerce").fillna(1)
    df["host_scale"] = pd.cut(df["host_listings_count"], [0, 2, 10, 50, 10**6],
                              labels=["个人(1-2)", "小型(3-10)", "专业(11-50)", "机构(50+)"]).astype(str)

    df.to_csv(os.path.join(CLEAN, "airbnb_listings_cleaned.csv.gz"), index=False, compression="gzip")

    # ---- 评论数据 ----
    rv = pd.read_csv(os.path.join(RAW, "reviews_detailed.csv.gz"),
                     usecols=["listing_id", "id", "date", "comments"], low_memory=False)
    n1 = len(rv)
    add_log(dataset, "原始数据", f"共 {n1} 条评论", n1)
    rv["comments"] = rv["comments"].astype(str)
    rv = rv[(rv["comments"].str.len() > 0) & (~rv["comments"].isin(["nan", "None"]))]
    add_log(dataset, "缺失值处理", "剔除空评论", len(rv))
    rv = rv.drop_duplicates(subset=["id"])
    add_log(dataset, "去重", "剔除重复评论", len(rv))
    rv["review_len"] = rv["comments"].str.len()
    rv["date"] = pd.to_datetime(rv["date"], errors="coerce").dt.date.astype(str)
    rv = rv.dropna(subset=["date"])
    rv = rv[["listing_id", "id", "date", "comments", "review_len"]]
    rv.to_csv(os.path.join(CLEAN, "airbnb_reviews_cleaned.csv.gz"), index=False, compression="gzip")
    return {"listings": int(len(df)), "reviews": int(len(rv)), "price_p99": float(p99),
            "neighbourhoods": int(df["neighbourhood_cleansed"].nunique()),
            "review_date_max": str(rv["date"].max())}


# ============================================================
# 3. Yelp 商家评论样本
# ============================================================
def clean_yelp():
    dataset = "Yelp评论样本"
    df = pd.read_csv(os.path.join(RAW, "yelp_reviews.csv"))
    n0 = len(df)
    add_log(dataset, "原始数据", f"共 {n0} 条商家评论", n0)

    # 1) 日期格式标准化（源数据为 DD/MM/YYYY，且带有多余引号）
    df["Date"] = (df["Date"].astype(str).str.replace('"', '', regex=False).str.strip())
    df["Date"] = pd.to_datetime(df["Date"], format="%d/%m/%Y", errors="coerce")
    add_log(dataset, "类型转换", "标准化DD/MM/YYYY日期并剔除无法解析的日期", int(df["Date"].notna().sum()))
    df = df.dropna(subset=["Date"])

    # 2) 评分合法性（1-5星整数）
    df["Rating"] = pd.to_numeric(df["Rating"], errors="coerce")
    df = df[df["Rating"].between(1, 5)]
    add_log(dataset, "异常值过滤", "剔除非1-5星评分", len(df))

    # 3) 去重 + 空评论剔除
    df = df.drop_duplicates(subset=["business_id", "Content"])
    df = df[df["Content"].astype(str).str.len() > 0]
    add_log(dataset, "去重/缺失值", "剔除重复与空评论", len(df))

    # 4) 特征衍生
    df["review_len"] = df["Content"].astype(str).str.len()
    df["word_count"] = df["Content"].astype(str).str.split().str.len()
    df["elite_flag"] = df["Eelite_status"].notna().astype(int)

    # 5) 文本情感打分（VADER 复合得分, -1~1）
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    sia = SentimentIntensityAnalyzer()
    df["sentiment"] = df["Content"].astype(str).map(lambda t: sia.polarity_scores(t)["compound"])
    df["sentiment_label"] = pd.cut(df["sentiment"], [-1.01, -0.05, 0.05, 1.01],
                                   labels=["负面", "中性", "正面"]).astype(str)

    df[["business_id", "business_name", "Date", "Rating", "review_len", "word_count",
        "elite_flag", "sentiment", "sentiment_label", "Reactions"]].to_csv(
        os.path.join(CLEAN, "yelp_reviews_cleaned.csv.gz"), index=False, compression="gzip")
    return {"rows": int(len(df)), "businesses": int(df["business_id"].nunique()),
            "avg_rating": round(float(df["Rating"].mean()), 2)}


# ============================================================
# 4. Reddit r/ChatGPT 社区评论
# ============================================================
def clean_reddit():
    dataset = "Reddit(r/ChatGPT)"
    df = pd.read_csv(os.path.join(RAW, "reddit_chatgpt_comments.csv"))
    n0 = len(df)
    add_log(dataset, "原始数据", f"共 {n0} 条社区评论", n0)

    df = df.rename(columns={"comment_body": "body"})
    # 1) 剔除已删除/移除的评论
    df = df[~df["body"].astype(str).isin(["[deleted]", "[removed]", "nan"])]
    add_log(dataset, "缺失值处理", "剔除已删除/移除的评论", len(df))

    # 2) 去重
    df = df.drop_duplicates(subset=["comment_id"])
    add_log(dataset, "去重", "剔除重复评论", len(df))

    # 3) 剔除超短灌水评论（<15字符）
    df = df[df["body"].astype(str).str.len() >= 15]
    add_log(dataset, "异常值过滤", "剔除<15字符的灌水评论", len(df))

    # 4) VADER 情感打分
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    sia = SentimentIntensityAnalyzer()
    df["sentiment"] = df["body"].astype(str).map(lambda t: sia.polarity_scores(t)["compound"])
    df["sentiment_label"] = pd.cut(df["sentiment"], [-1.01, -0.05, 0.05, 1.01],
                                   labels=["负面", "中性", "正面"]).astype(str)
    df["review_len"] = df["body"].astype(str).str.len()

    df[["comment_id", "body", "sentiment", "sentiment_label", "review_len"]].to_csv(
        os.path.join(CLEAN, "reddit_chatgpt_cleaned.csv.gz"), index=False, compression="gzip")
    return {"rows": int(len(df)), "neg_ratio": round(float((df["sentiment_label"] == "负面").mean()), 4)}


if __name__ == "__main__":
    summary = {}
    summary["taobao"] = clean_taobao()
    summary["airbnb"] = clean_airbnb()
    summary["yelp"] = clean_yelp()
    summary["reddit"] = clean_reddit()

    pd.DataFrame(log).to_csv(os.path.join(OUT, "tables", "cleaning_report.csv"),
                             index=False, encoding="utf-8-sig")
    with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("\n=== 清洗完成 ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
