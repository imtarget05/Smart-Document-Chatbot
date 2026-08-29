# Airflow service image for the Smart Document Chatbot.
# Adds the project ingestion DAGs and the deps they need (psycopg2, requests).
FROM apache/airflow:2.9.3

USER root
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt
USER airflow

# DAGs are mounted at /opt/airflow/dags via the compose volume, so no COPY needed.
