-- ============================================================
-- 04_Yelp与Reddit舆情分析.sql —— 用户之声/舆情洞察视角
-- 数据: Yelp 商家评论样本 + Reddit r/ChatGPT 社区评论（清洗后）
-- 分析: 评分结构 / 情感分布 / 高价值评论者 / AI产品用户之声
-- ============================================================

-- Q1 Yelp评分分布（满意度结构）
-- @QUERY: yp_rating_dist
SELECT rating AS 星级,
       COUNT(*) AS 评论数,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM yelp_reviews), 1) AS 占比pct,
       ROUND(AVG(word_count), 0) AS 平均词数,
       ROUND(AVG(sentiment), 3) AS 平均情感得分
FROM yelp_reviews
GROUP BY rating
ORDER BY rating;

-- Q2 Yelp情感标签分布
-- @QUERY: yp_sentiment_dist
SELECT sentiment_label AS 情感标签,
       COUNT(*) AS 评论数,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM yelp_reviews), 1) AS 占比pct,
       ROUND(AVG(rating), 2) AS 平均星级
FROM yelp_reviews
GROUP BY sentiment_label;

-- Q3 Yelp精英用户 vs 普通用户评论特征
-- @QUERY: yp_elite_vs_normal
SELECT CASE WHEN elite_flag=1 THEN '精英用户' ELSE '普通用户' END AS 用户类型,
       COUNT(*) AS 评论数,
       ROUND(AVG(rating), 2) AS 平均星级,
       ROUND(AVG(word_count), 0) AS 平均词数,
       ROUND(AVG(sentiment), 3) AS 平均情感得分
FROM yelp_reviews
GROUP BY elite_flag;

-- Q4 Yelp差评(1-2星)的情感强度（差评管理优先级）
-- @QUERY: yp_negative
SELECT business_name AS 商家,
       rating AS 星级,
       ROUND(sentiment, 3) AS 情感得分,
       word_count AS 词数
FROM yelp_reviews
WHERE rating <= 2
ORDER BY sentiment ASC
LIMIT 10;

-- Q5 Reddit情感分布（AI产品社区情绪温度计）
-- @QUERY: rd_sentiment_dist
SELECT sentiment_label AS 情感标签,
       COUNT(*) AS 评论数,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM reddit_chatgpt), 1) AS 占比pct,
       ROUND(AVG(review_len), 0) AS 平均字符数
FROM reddit_chatgpt
GROUP BY sentiment_label;

-- Q6 Reddit评论长度与情感的关系（长评是否更负面）
-- @QUERY: rd_len_vs_sentiment
SELECT CASE WHEN review_len < 50  THEN '<50字'
            WHEN review_len < 150 THEN '50-150字'
            WHEN review_len < 300 THEN '150-300字'
            WHEN review_len < 600 THEN '300-600字'
            ELSE '600字以上' END AS 评论长度档,
       COUNT(*) AS 评论数,
       ROUND(AVG(sentiment), 3) AS 平均情感得分,
       ROUND(SUM(CASE WHEN sentiment_label='负面' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS 负面占比pct
FROM reddit_chatgpt
GROUP BY 评论长度档
ORDER BY 评论长度档;

-- Q7 AI产品用户之声: 核心痛点主题出现频次（SQL模糊匹配）
-- @QUERY: rd_pain_points
SELECT '幻觉/胡编(hallucination)' AS 痛点主题,
       COUNT(CASE WHEN body LIKE '%hallucinat%' THEN 1 END) AS 提及数 FROM reddit_chatgpt
UNION ALL
SELECT '回答错误(wrong)', COUNT(CASE WHEN body LIKE '%wrong%' THEN 1 END) FROM reddit_chatgpt
UNION ALL
SELECT '封号/审查(banned)', COUNT(CASE WHEN body LIKE '%banned%' OR body LIKE '%ban me%' THEN 1 END) FROM reddit_chatgpt
UNION ALL
SELECT '使用限制(limit)', COUNT(CASE WHEN body LIKE '%limit%' THEN 1 END) FROM reddit_chatgpt
UNION ALL
SELECT '付费/订阅(pay)', COUNT(CASE WHEN body LIKE '%subscription%' OR body LIKE '%paying%' THEN 1 END) FROM reddit_chatgpt
UNION ALL
SELECT '好用/惊艳(amazing)', COUNT(CASE WHEN body LIKE '%amazing%' OR body LIKE '%impressive%' THEN 1 END) FROM reddit_chatgpt
UNION ALL
SELECT '替代品/竞争(better than)', COUNT(CASE WHEN body LIKE '%better than%' THEN 1 END) FROM reddit_chatgpt
UNION ALL
SELECT '工作替代(job)', COUNT(CASE WHEN body LIKE '%job%' THEN 1 END) FROM reddit_chatgpt;

-- Q8 情感极值样本（最负面评论示例，用于痛点挖掘）
-- @QUERY: rd_most_negative
SELECT body AS 评论内容, ROUND(sentiment, 3) AS 情感得分
FROM reddit_chatgpt
WHERE review_len BETWEEN 80 AND 400
ORDER BY sentiment ASC
LIMIT 8;
