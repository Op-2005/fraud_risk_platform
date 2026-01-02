-- Create Glue database (run in Athena query editor)
CREATE DATABASE IF NOT EXISTS fraud_demo;

-- Create table for fraud events (partitioned by date and hour)
CREATE EXTERNAL TABLE IF NOT EXISTS fraud_demo.fraud_events (
  event_id string,
  ts timestamp,
  user_id string,
  amount double,
  currency string,
  country string,
  device_id string,
  ip string,
  merchant_id string,
  risk_score double,
  decision string,
  reasons array<string>
)
PARTITIONED BY (
  dt string,
  hour string
)
STORED AS PARQUET
LOCATION 's3://fraud-events-245872626324-us-west-2/events/'
TBLPROPERTIES (
  'projection.enabled' = 'true',
  'projection.dt.type' = 'date',
  'projection.dt.format' = 'yyyy-MM-dd',
  'projection.dt.range' = '2025-01-01,NOW',
  'projection.hour.type' = 'integer',
  'projection.hour.range' = '0,23',
  'projection.hour.interval' = '1',
  'storage.location.template' = 's3://fraud-events-245872626324-us-west-2/events/dt=${dt}/hour=${hour}/'
);

-- Repair partitions (run after table creation)
MSCK REPAIR TABLE fraud_demo.fraud_events;

