-- Drop n8n analytics tables (prune n8n bloat, superseded by agent/airflow pipeline)
DROP TABLE IF EXISTS document_analytics;
DROP TABLE IF EXISTS escalation_queue;
DROP TABLE IF EXISTS document_summaries;
