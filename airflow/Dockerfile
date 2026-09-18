# Airflow service image for the Smart Document Chatbot.
# Adds the project ingestion DAGs and the deps they need (psycopg2, requests).
FROM apache/airflow:2.9.3

USER root
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt
USER airflow

# DAGs are mounted at /opt/airflow/dags via the compose volume, so no COPY needed.
# The project itself (finetune/, eval/, scripts/) is mounted read-only at
# /opt/smartdoc so the retrain DAG can run finetune/build_dataset.py with
# FINETUNE_ROOT=/opt/smartdoc. Without that mount the DAG fails loudly.
ENV FINETUNE_ROOT=/opt/smartdoc
