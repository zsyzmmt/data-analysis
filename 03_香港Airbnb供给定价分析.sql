-- ============================================================
-- 03_香港Airbnb供给与定价分析.sql —— 策略运营/定价视角
-- 数据: Inside Airbnb 香港房源与评论（清洗后）
-- 分析: 区域供给 / 房型定价 / 价格影响因素 / 房东生态 / 需求季节性
-- ============================================================

-- Q1 区域供给与价格概览（Top15供给区域）
-- @QUERY: ab_neighbourhood
SELECT neighbourhood AS 区域,
       COUNT(*) AS 房源数,
       ROUND(AVG(price_winsor), 0) AS 均价,
       ROUND(AVG(review_scores_rating), 1) AS 平均评分,
       ROUND(AVG(occupancy_ratio) * 100, 1) AS 供给紧张度pct
FROM airbnb_listings
GROUP BY neighbourhood
ORDER BY 房源数 DESC
LIMIT 15;

-- Q2 房型供给结构与定价
-- @QUERY: ab_room_type
SELECT room_type AS 房型,
       COUNT(*) AS 房源数,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM airbnb_listings), 1) AS 供给占比pct,
       ROUND(AVG(price_winsor), 0) AS 均价,
       ROUND(AVG(review_scores_rating), 1) AS 平均评分,
       ROUND(AVG(minimum_nights), 1) AS 平均最小入住晚数
FROM airbnb_listings
GROUP BY room_type
ORDER BY 房源数 DESC;

-- Q3 区域x房型均价矩阵（Top6区域）
-- @QUERY: ab_region_room_price
WITH top_region AS (
    SELECT neighbourhood FROM airbnb_listings
    GROUP BY neighbourhood ORDER BY COUNT(*) DESC LIMIT 6
)
SELECT l.neighbourhood AS 区域,
       MAX(CASE WHEN l.room_type='Entire home/apt' THEN ROUND(AVG_,0) END) AS 整套房源均价,
       MAX(CASE WHEN l.room_type='Private room'    THEN ROUND(AVG_,0) END) AS 私人房间均价,
       MAX(CASE WHEN l.room_type='Shared room'     THEN ROUND(AVG_,0) END) AS 合住房间均价
FROM (
    SELECT neighbourhood, room_type, AVG(price_winsor) AS AVG_
    FROM airbnb_listings GROUP BY neighbourhood, room_type
) l
WHERE l.neighbourhood IN (SELECT neighbourhood FROM top_region)
GROUP BY l.neighbourhood;

-- Q4 定价因素1: 评分档位 vs 均价
-- @QUERY: ab_price_by_rating
SELECT CASE WHEN review_scores_rating IS NULL THEN '无评分'
            WHEN review_scores_rating < 4.0 THEN '4.0以下'
            WHEN review_scores_rating < 4.5 THEN '4.0-4.5'
            WHEN review_scores_rating < 4.8 THEN '4.5-4.8'
            ELSE '4.8-5.0' END AS 评分档,
       COUNT(*) AS 房源数,
       ROUND(AVG(price_winsor), 0) AS 均价,
       ROUND(AVG(number_of_reviews), 1) AS 平均评论数
FROM airbnb_listings
GROUP BY 评分档
ORDER BY 均价;

-- Q5 定价因素2: 评论数档位 vs 均价（口碑积累与溢价）
-- @QUERY: ab_price_by_reviews
SELECT CASE WHEN number_of_reviews = 0 THEN '0条(新房源)'
            WHEN number_of_reviews <= 10 THEN '1-10条'
            WHEN number_of_reviews <= 50 THEN '11-50条'
            WHEN number_of_reviews <= 200 THEN '51-200条'
            ELSE '200条以上' END AS 评论数档,
       COUNT(*) AS 房源数,
       ROUND(AVG(price_winsor), 0) AS 均价,
       ROUND(AVG(review_scores_rating), 1) AS 平均评分
FROM airbnb_listings
GROUP BY 评论数档
ORDER BY 房源数 DESC;

-- Q6 定价因素3: 超级房东溢价
-- @QUERY: ab_superhost_premium
SELECT (host_is_superhost = 't') AS 超级房东,
       COUNT(*) AS 房源数,
       ROUND(AVG(price_winsor), 0) AS 均价,
       ROUND(AVG(review_scores_rating), 1) AS 平均评分,
       ROUND(AVG(estimated_revenue_l365d), 0) AS 年化预估收入
FROM airbnb_listings
GROUP BY 超级房东;

-- Q7 定价因素4: 可住人数与价格弹性
-- @QUERY: ab_price_by_accommodates
SELECT accommodates AS 可住人数,
       COUNT(*) AS 房源数,
       ROUND(AVG(price_winsor), 0) AS 均价,
       ROUND(AVG(price_winsor) / accommodates, 0) AS 人均每晚价格
FROM airbnb_listings
WHERE accommodates BETWEEN 1 AND 8
GROUP BY accommodates
ORDER BY 可住人数;

-- Q8 房东生态: 规模分层与供给集中度
-- @QUERY: ab_host_scale
SELECT host_scale AS 房东规模,
       COUNT(*) AS 房源数,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM airbnb_listings), 1) AS 房源占比pct,
       COUNT(DISTINCT host_id) AS 房东数,
       ROUND(AVG(price_winsor), 0) AS 均价,
       ROUND(AVG(estimated_revenue_l365d), 0) AS 房均年化收入
FROM airbnb_listings
GROUP BY host_scale
ORDER BY 房源数 DESC;

-- Q9 供给集中度: 头部10%房东控制了多少房源（二八法则验证）
-- @QUERY: ab_host_concentration
WITH host_cnt AS (
    SELECT host_id, COUNT(*) AS n FROM airbnb_listings GROUP BY host_id
),
ranked AS (
    SELECT host_id, n,
           ROW_NUMBER() OVER (ORDER BY n DESC) AS rk,
           SUM(n) OVER (ORDER BY n DESC) AS cum_listings,
           SUM(SUM(n)) OVER () AS total
    FROM host_cnt GROUP BY host_id, n
)
SELECT ROUND(MAX(cum_listings) * 100.0 / total, 1) AS 头部10pct房东控制房源占比pct
FROM ranked WHERE rk <= CAST((SELECT COUNT(*) FROM host_cnt) * 0.1 AS INT);

-- Q10 需求季节性: 近3年评论量月度分布（评论量≈入住量代理指标）
-- @QUERY: ab_review_season
SELECT strftime('%Y-%m', date) AS 月份,
       COUNT(*) AS 评论数,
       COUNT(DISTINCT listing_id) AS 有评论房源数
FROM airbnb_reviews
WHERE date >= '2023-07'
GROUP BY 月份
ORDER BY 月份;

-- Q11 月份维度季节性: 全年12个月平均评论量（跨年聚合）
-- @QUERY: ab_review_month_of_year
SELECT CAST(strftime('%m', date) AS INT) AS 月份,
       COUNT(*) AS 总评论数,
       ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT strftime('%Y', date)), 0) AS 年均月评论量
FROM airbnb_reviews
WHERE date >= '2019-01'
GROUP BY 月份
ORDER BY 月份;

-- Q12 高价值房源画像（年化收入Top25%的特征）
-- @QUERY: ab_top_revenue_profile
WITH rev AS (
    SELECT id, neighbourhood, room_type, price_winsor, review_scores_rating,
           estimated_revenue_l365d, accommodates, host_scale,
           NTILE(4) OVER (ORDER BY estimated_revenue_l365d DESC) AS 收入四分位
    FROM airbnb_listings
    WHERE estimated_revenue_l365d IS NOT NULL
)
SELECT CASE WHEN 收入四分位=1 THEN 'Top25%(高收入)' ELSE '其余75%' END AS 收入分层,
       ROUND(AVG(price_winsor), 0) AS 均价,
       ROUND(AVG(review_scores_rating), 1) AS 平均评分,
       ROUND(AVG(accommodates), 1) AS 平均可住人数,
       ROUND(AVG(estimated_revenue_l365d), 0) AS 平均年化收入
FROM rev
GROUP BY CASE WHEN 收入四分位=1 THEN 'Top25%(高收入)' ELSE '其余75%' END;
