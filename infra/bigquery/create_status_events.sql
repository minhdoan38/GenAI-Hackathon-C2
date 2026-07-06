CREATE TABLE IF NOT EXISTS `citymind-ai-500910.citymind.report_status_events` (
  report_id STRING NOT NULL,
  status STRING NOT NULL,
  note STRING,
  created_at TIMESTAMP NOT NULL
);
