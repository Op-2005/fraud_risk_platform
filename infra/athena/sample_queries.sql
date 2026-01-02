-- Sample Athena queries for fraud detection platform

-- 1. Daily event count
SELECT 
  dt,
  COUNT(*) as event_count,
  COUNT(DISTINCT user_id) as unique_users,
  SUM(CASE WHEN decision = 'block' THEN 1 ELSE 0 END) as blocked_count
FROM fraud_demo.fraud_events
WHERE dt >= CURRENT_DATE - INTERVAL '7' DAY
GROUP BY dt
ORDER BY dt DESC;

-- 2. High-risk transactions
SELECT 
  event_id,
  user_id,
  amount,
  currency,
  risk_score,
  decision,
  reasons
FROM fraud_demo.fraud_events
WHERE risk_score > 0.7
  AND dt = CURRENT_DATE
ORDER BY risk_score DESC
LIMIT 100;

-- 3. Merchant fraud rate
SELECT 
  merchant_id,
  COUNT(*) as total_txns,
  SUM(CASE WHEN decision = 'block' THEN 1 ELSE 0 END) as blocked_txns,
  ROUND(SUM(CASE WHEN decision = 'block' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as fraud_rate_pct,
  AVG(risk_score) as avg_risk_score
FROM fraud_demo.fraud_events
WHERE dt >= CURRENT_DATE - INTERVAL '7' DAY
GROUP BY merchant_id
HAVING COUNT(*) >= 10
ORDER BY fraud_rate_pct DESC
LIMIT 20;

-- 4. User behavior patterns
SELECT 
  user_id,
  COUNT(*) as txn_count,
  AVG(amount) as avg_amount,
  COUNT(DISTINCT device_id) as device_count,
  COUNT(DISTINCT ip) as ip_count,
  COUNT(DISTINCT country) as country_count,
  MAX(risk_score) as max_risk_score
FROM fraud_demo.fraud_events
WHERE dt >= CURRENT_DATE - INTERVAL '7' DAY
GROUP BY user_id
HAVING COUNT(*) >= 5
ORDER BY max_risk_score DESC
LIMIT 50;

-- 5. Hourly transaction volume
SELECT 
  dt,
  hour,
  COUNT(*) as txn_count,
  AVG(risk_score) as avg_risk_score,
  SUM(CASE WHEN decision = 'block' THEN 1 ELSE 0 END) as blocked_count
FROM fraud_demo.fraud_events
WHERE dt >= CURRENT_DATE - INTERVAL '1' DAY
GROUP BY dt, hour
ORDER BY dt DESC, hour DESC;

