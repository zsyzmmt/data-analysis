-- ============================================================
-- 02_淘宝用户行为分析.sql —— 电商增长/用户运营视角
-- 数据: 阿里天池 UserBehavior 用户行为数据（清洗后）
-- 分析: 漏斗转化 / 活跃时段 / RFM分层 / 类目四象限 / 复购
-- 约定: 每条查询前以行首 @QUERY 注释标记导出文件名
-- ============================================================

-- Q1 总体行为量与用户规模（数据概览）
-- @QUERY: tb_overview
SELECT
    COUNT(*)                                              AS 行为总量,
    COUNT(DISTINCT user_id)                               AS 活跃用户数,
    COUNT(DISTINCT item_id)                               AS 触达商品数,
    COUNT(DISTINCT category_id)                           AS 触达类目数,
    ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT user_id), 1)     AS 人均行为次数
FROM taobao_behavior;

-- Q2 AARRR行为漏斗（用户级）: 浏览->收藏/加购->购买
-- @QUERY: tb_funnel
WITH user_stage AS (
    SELECT user_id,
           MAX(CASE WHEN behavior_type='pv'   THEN 1 ELSE 0 END) AS did_pv,
           MAX(CASE WHEN behavior_type='fav'   THEN 1 ELSE 0 END) AS did_fav,
           MAX(CASE WHEN behavior_type='cart' THEN 1 ELSE 0 END) AS did_cart,
           MAX(CASE WHEN behavior_type='buy'  THEN 1 ELSE 0 END) AS did_buy
    FROM taobao_behavior GROUP BY user_id
)
SELECT '浏览pv' AS 漏斗层级, SUM(did_pv) AS 用户数 FROM user_stage
UNION ALL SELECT '收藏fav', SUM(did_fav) FROM user_stage
UNION ALL SELECT '加购cart', SUM(did_cart) FROM user_stage
UNION ALL SELECT '购买buy',  SUM(did_buy)  FROM user_stage;

-- Q3 行为总量结构（行为级占比）
-- @QUERY: tb_behavior_mix
SELECT behavior_type AS 行为类型,
       COUNT(*) AS 行为量,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM taobao_behavior), 2) AS 占比pct
FROM taobao_behavior
GROUP BY behavior_type
ORDER BY 行为量 DESC;

-- Q4 分时段行为分布（运营排期依据）
-- @QUERY: tb_hourly
SELECT hour AS 小时,
       SUM(CASE WHEN behavior_type='pv'   THEN 1 ELSE 0 END) AS pv量,
       SUM(CASE WHEN behavior_type='fav' THEN 1 ELSE 0 END) AS 收藏量,
       SUM(CASE WHEN behavior_type='cart' THEN 1 ELSE 0 END) AS 加购量,
       SUM(CASE WHEN behavior_type='buy'  THEN 1 ELSE 0 END) AS 购买量,
       COUNT(DISTINCT user_id) AS 活跃用户数
FROM taobao_behavior
GROUP BY hour
ORDER BY hour;

-- Q5 每日活跃与转化趋势（若数据覆盖多天）
-- @QUERY: tb_daily
SELECT date AS 日期,
       COUNT(DISTINCT user_id) AS 活跃用户数,
       SUM(CASE WHEN behavior_type='pv'  THEN 1 ELSE 0 END) AS pv量,
       SUM(CASE WHEN behavior_type='buy' THEN 1 ELSE 0 END) AS 购买量,
       ROUND(SUM(CASE WHEN behavior_type='buy' THEN 1 ELSE 0 END) * 100.0 /
             NULLIF(SUM(CASE WHEN behavior_type='pv' THEN 1 ELSE 0 END), 0), 2) AS 购买转化率pct
FROM taobao_behavior
GROUP BY date
ORDER BY date;

-- Q6 RFM用户价值分层（R=最近一次购买距今, F=购买次数, M=购买件数）
-- @QUERY: tb_rfm_raw
WITH buy AS (
    SELECT user_id,
           COUNT(*)                              AS F_购买次数,
           julianday(MAX(date)) - julianday(MIN(date)) AS 活跃跨度天
    FROM taobao_behavior
    WHERE behavior_type = 'buy'
    GROUP BY user_id
),
rfm AS (
    SELECT b.user_id,
           b.F_购买次数,
           ROW_NUMBER() OVER (ORDER BY b.F_购买次数 DESC) AS 购买次数排名
    FROM buy b
)
SELECT * FROM rfm ORDER BY 购买次数排名 LIMIT 20;

-- Q7 用户购买次数分布（复购结构）
-- @QUERY: tb_repurchase
WITH user_buy AS (
    SELECT user_id, COUNT(*) AS 购买次数
    FROM taobao_behavior WHERE behavior_type='buy'
    GROUP BY user_id
)
SELECT CASE WHEN 购买次数=1 THEN '1次(单次购买)'
            WHEN 购买次数 BETWEEN 2 AND 3 THEN '2-3次'
            WHEN 购买次数 BETWEEN 4 AND 10 THEN '4-10次'
            ELSE '10次以上' END AS 购买频次分层,
       COUNT(*) AS 用户数,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM user_buy), 2) AS 占比pct
FROM user_buy
GROUP BY 购买频次分层
ORDER BY 用户数 DESC;

-- Q8 类目流量-转化四象限（运营资源分配）
-- @QUERY: tb_category
SELECT category_id AS 类目ID,
       SUM(CASE WHEN behavior_type='pv'   THEN 1 ELSE 0 END) AS 浏览量,
       COUNT(DISTINCT CASE WHEN behavior_type='pv' THEN user_id END) AS 浏览人数,
       SUM(CASE WHEN behavior_type='buy'  THEN 1 ELSE 0 END) AS 购买量,
       ROUND(SUM(CASE WHEN behavior_type='buy' THEN 1 ELSE 0 END) * 100.0 /
             NULLIF(SUM(CASE WHEN behavior_type='pv' THEN 1 ELSE 0 END), 0), 2) AS 购买转化率pct
FROM taobao_behavior
GROUP BY category_id
HAVING 浏览量 >= 200
ORDER BY 浏览量 DESC;

-- Q9 高转化类目 TOP10（低流量高转化=潜力类目）
-- @QUERY: tb_category_top_conv
SELECT category_id AS 类目ID,
       SUM(CASE WHEN behavior_type='pv'  THEN 1 ELSE 0 END) AS 浏览量,
       SUM(CASE WHEN behavior_type='buy' THEN 1 ELSE 0 END) AS 购买量,
       ROUND(SUM(CASE WHEN behavior_type='buy' THEN 1 ELSE 0 END) * 100.0 /
             NULLIF(SUM(CASE WHEN behavior_type='pv' THEN 1 ELSE 0 END), 0), 2) AS 购买转化率pct
FROM taobao_behavior
GROUP BY category_id
HAVING 浏览量 >= 200
ORDER BY 购买转化率pct DESC
LIMIT 10;

-- Q10 购买用户 vs 未购买用户行为深度对比（用户画像差异）
-- @QUERY: tb_buyer_vs_nonbuyer
WITH user_stat AS (
    SELECT user_id,
           MAX(CASE WHEN behavior_type='buy' THEN 1 ELSE 0 END) AS is_buyer,
           COUNT(*) AS 行为总数,
           COUNT(DISTINCT item_id) AS 触达商品数,
           COUNT(DISTINCT category_id) AS 触达类目数,
           SUM(CASE WHEN behavior_type='fav'  THEN 1 ELSE 0 END) AS 收藏数,
           SUM(CASE WHEN behavior_type='cart' THEN 1 ELSE 0 END) AS 加购数
    FROM taobao_behavior GROUP BY user_id
)
SELECT CASE WHEN is_buyer=1 THEN '购买用户' ELSE '未购买用户' END AS 用户群,
       COUNT(*) AS 用户数,
       ROUND(AVG(行为总数), 1) AS 平均行为次数,
       ROUND(AVG(触达商品数), 1) AS 平均触达商品数,
       ROUND(AVG(触达类目数), 1) AS 平均触达类目数,
       ROUND(AVG(收藏数), 2) AS 平均收藏数,
       ROUND(AVG(加购数), 2) AS 平均加购数
FROM user_stat
GROUP BY is_buyer;

-- Q11 收藏/加购到购买的转化效率（购物车运营抓手）
-- @QUERY: tb_intermediate_conv
WITH stage AS (
    SELECT user_id,
           MAX(CASE WHEN behavior_type='fav'  THEN 1 ELSE 0 END) AS did_fav,
           MAX(CASE WHEN behavior_type='cart' THEN 1 ELSE 0 END) AS did_cart,
           MAX(CASE WHEN behavior_type='buy' THEN 1 ELSE 0 END) AS did_buy
    FROM taobao_behavior GROUP BY user_id
)
SELECT
    ROUND(SUM(did_fav) * 100.0 / COUNT(*), 2)            AS 收藏用户占比pct,
    ROUND(SUM(did_cart) * 100.0 / COUNT(*), 2)           AS 加购用户占比pct,
    ROUND(SUM(CASE WHEN did_fav=1 AND did_buy=1 THEN 1 ELSE 0 END) * 100.0
          / NULLIF(SUM(did_fav), 0), 2)                  AS 收藏转购买率pct,
    ROUND(SUM(CASE WHEN did_cart=1 AND did_buy=1 THEN 1 ELSE 0 END) * 100.0
          / NULLIF(SUM(did_cart), 0), 2)                 AS 加购转购买率pct
FROM stage;

-- Q12 用户活跃度分层（帕累托/二八分析）
-- @QUERY: tb_user_activity_tier
WITH user_act AS (
    SELECT user_id, COUNT(*) AS 行为次数 FROM taobao_behavior GROUP BY user_id
),
ranked AS (
    SELECT user_id, 行为次数,
           NTILE(10) OVER (ORDER BY 行为次数) AS 十分位
    FROM user_act
)
SELECT CASE WHEN 十分位=1 THEN 'D1(最不活跃)' WHEN 十分位=5 THEN 'D5(中位)'
            WHEN 十分位=9 THEN 'D9' WHEN 十分位=10 THEN 'D10(最活跃)' ELSE NULL END AS 活跃度分层,
       COUNT(*) AS 用户数,
       SUM(行为次数) AS 行为总量,
       ROUND(SUM(行为次数) * 100.0 / (SELECT COUNT(*) FROM taobao_behavior), 2) AS 行为量占比pct
FROM ranked
WHERE 十分位 IN (1, 5, 9, 10)
GROUP BY 十分位
ORDER BY 十分位;
