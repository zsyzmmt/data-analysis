-- ============================================================
-- 01_建表DDL.sql —— 数据入库（SQLite）
-- 项目: 多源电商与本地生活用户行为数据分析
-- 说明: 清洗后的数据由 scripts/step2_sql_analysis.py 按下列建表语句
--       批量导入 data/analysis.db，后续分析全部基于 SQL 完成
-- ============================================================

DROP TABLE IF EXISTS taobao_behavior;
CREATE TABLE taobao_behavior (
    user_id       INTEGER NOT NULL,   -- 用户ID（脱敏）
    item_id       INTEGER NOT NULL,   -- 商品ID（脱敏）
    category_id   INTEGER NOT NULL,   -- 商品类目ID
    behavior_type TEXT    NOT NULL,   -- 行为类型: pv/fav/cart/buy
    datetime      TEXT,              -- 行为发生时间（北京时间）
    date          TEXT,              -- 日期
    hour          INTEGER,           -- 小时 0-23
    weekday       INTEGER            -- 星期 1-7
);

DROP TABLE IF EXISTS airbnb_listings;
CREATE TABLE airbnb_listings (
    id                        INTEGER PRIMARY KEY, -- 房源ID
    host_id                   INTEGER,             -- 房东ID
    host_name                 TEXT,                -- 房东昵称
    host_is_superhost         TEXT,                -- 是否超级房东 t/f
    host_listings_count         INTEGER,             -- 房东名下房源总数
    host_scale                TEXT,                -- 房东规模分层
    neighbourhood             TEXT,                -- 所在区域
    room_type                 TEXT,                -- 房型
    property_type             TEXT,                -- 物业类型
    accommodates              INTEGER,             -- 可住人数
    bedrooms                  REAL,                -- 卧室数
    beds                      REAL,                -- 床位数
    price                     REAL,                -- 挂牌价（原币种）
    price_winsor              REAL,                -- 缩尾后价格（99分位封顶）
    minimum_nights            INTEGER,             -- 最小入住晚数
    number_of_reviews         INTEGER,             -- 累计评论数
    number_of_reviews_ltm     INTEGER,             -- 近12月评论数
    review_scores_rating      REAL,                -- 综合评分
    availability_365         INTEGER,             -- 未来365天可订天数
    estimated_revenue_l365d   REAL,                -- 年化预估收入
    occupancy_ratio           REAL                 -- 供给紧张度(1-可订率)
);

DROP TABLE IF EXISTS airbnb_reviews;
CREATE TABLE airbnb_reviews (
    listing_id INTEGER NOT NULL, -- 房源ID
    id        TEXT,             -- 评论ID
    date      TEXT,            -- 评论日期
    comments  TEXT,            -- 评论内容
    review_len INTEGER         -- 评论长度（字符）
);

DROP TABLE IF EXISTS yelp_reviews;
CREATE TABLE yelp_reviews (
    business_id     TEXT,    -- 商家ID
    business_name   TEXT,    -- 商家名称
    review_date     TEXT,    -- 评论日期
    rating          REAL,   -- 星级 1-5
    review_len      INTEGER,-- 评论字符数
    word_count      INTEGER,-- 评论词数
    elite_flag      INTEGER,-- 是否精英用户评论
    sentiment       REAL,   -- VADER情感得分 -1~1
    sentiment_label TEXT    -- 情感标签: 正面/中性/负面
);

DROP TABLE IF EXISTS reddit_chatgpt;
CREATE TABLE reddit_chatgpt (
    comment_id      TEXT,    -- 评论ID
    body            TEXT,    -- 评论内容
    sentiment       REAL,   -- VADER情感得分 -1~1
    sentiment_label TEXT,   -- 情感标签
    review_len      INTEGER -- 评论字符数
);
