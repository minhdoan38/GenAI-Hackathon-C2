CREATE SCHEMA IF NOT EXISTS `PROJECT_ID.citymind`
OPTIONS(location="US");

CREATE TABLE IF NOT EXISTS `PROJECT_ID.citymind.reports` (
  report_id STRING NOT NULL,
  created_at TIMESTAMP NOT NULL,
  description STRING,
  latitude FLOAT64,
  longitude FLOAT64,
  category STRING,
  severity INT64,
  confidence FLOAT64,
  summary STRING,
  recommendation STRING,
  priority STRING,
  estimated_impact STRING,
  evidence ARRAY<STRING>,
  uncertainty ARRAY<STRING>,
  urban_context STRING,
  image_gcs_uri STRING
)
PARTITION BY DATE(created_at)
CLUSTER BY category, priority;
