from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os
import uuid
import json
import requests

# Base URLs inside the Docker network
BACKEND_URL = "http://backend:8080/api/documents"
QDRANT_URL = "http://qdrant:6333"

# Default API URLs for LLM inside Docker
# Overridden by environment variables or configuration config
OLLAMA_URL = os.getenv("AIRFLOW_OLLAMA_URL", "http://ollama:11434")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(seconds=15),
}

dag = DAG(
    'document_etl',
    default_args=default_args,
    description='Smart Document Chatbot - Local MLOps ETL Pipeline',
    schedule_interval=None,
    catchup=False,
)

def parse_document_fn(**kwargs):
    # Retrieve configuration sent from backend trigger
    conf = kwargs['dag_run'].conf
    document_id = conf.get('document_id')
    file_path = conf.get('file_path')
    file_type = conf.get('file_type')
    
    # Path inside the Airflow shared volume
    filename = os.path.basename(file_path)
    airflow_filepath = os.path.join('/opt/airflow/uploads', filename)
    
    print(f"Starting parsing task for doc ID: {document_id}, path: {airflow_filepath}")
    
    if not os.path.exists(airflow_filepath):
        raise FileNotFoundError(f"File not found in shared storage: {airflow_filepath}")
        
    text = ""
    if file_type == "pdf":
        from pypdf import PdfReader
        reader = PdfReader(airflow_filepath)
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
    elif file_type in ["docx", "doc"]:
        import docx
        doc = docx.Document(airflow_filepath)
        for para in doc.paragraphs:
            text += para.text + "\n"
    elif file_type == "txt":
        with open(airflow_filepath, 'r', encoding='utf-8') as f:
            text = f.read()
    else:
        raise ValueError(f"Unsupported file type in ETL pipeline: {file_type}")
        
    print(f"Extraction successful. Text length: {len(text)} characters.")
    
    # Save the extracted text to a temporary work file so subsequent tasks can read it
    temp_dir = '/opt/airflow/tmp'
    os.makedirs(temp_dir, exist_ok=True)
    temp_filepath = os.path.join(temp_dir, f"extracted_{document_id}.txt")
    with open(temp_filepath, 'w', encoding='utf-8') as f:
        f.write(text)
        
    # Pass path via XCom
    return temp_filepath

def generate_insights_fn(**kwargs):
    conf = kwargs['dag_run'].conf
    document_id = conf.get('document_id')
    
    # Get the path of the extracted text file
    ti = kwargs['ti']
    temp_filepath = ti.xcom_pull(task_ids='parse_document')
    
    with open(temp_filepath, 'r', encoding='utf-8') as f:
        full_text = f.read()
        
    preview_text = full_text[:15000]
    
    print(f"Generating summary & suggested questions for doc ID: {document_id}")
    
    prompt = f"""You are a professional document analyst. Analyze the following document text and generate two things:
1. An Executive Summary: A concise high-level summary (3-5 bullet points) of the main topics and conclusions of the document.
2. Suggested Questions: 5 highly relevant and insightful questions that a user would likely ask about this document.

Return your response strictly in the following JSON format without any markdown wrapper (no ```json or ```):
{{
  "summary": "• Point 1\\n• Point 2\\n• Point 3",
  "suggestedQuestions": [
    "Question 1?",
    "Question 2?",
    "Question 3?",
    "Question 4?",
    "Question 5?"
  ]
}}

Document Text:
{preview_text}"""

    # Call Ollama local DeepSeek completion endpoint
    url = f"{OLLAMA_URL}/api/chat"
    payload = {
        "model": "deepseek-r1:1.5b",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant. Output ONLY valid JSON."},
            {"role": "user", "content": prompt}
        ],
        "options": {
            "temperature": 0.3
        },
        "stream": False
    }
    
    response = requests.post(url, json=payload, timeout=60)
    response.raise_for_status()
    
    result = response.json()
    content = result['message']['content']
    
    # Clean markdown wrapper if LLM returned it
    if "```" in content:
        content = content.replace("```json", "").replace("```", "").strip()
        
    # Validate it parses as JSON
    parsed = json.loads(content)
    
    # Save insights to temporary JSON file
    temp_insights_path = temp_filepath.replace(".txt", "_insights.json")
    with open(temp_insights_path, 'w', encoding='utf-8') as f:
        json.dump(parsed, f)
        
    return temp_insights_path

def embed_and_index_fn(**kwargs):
    conf = kwargs['dag_run'].conf
    document_id = conf.get('document_id')
    file_name = conf.get('file_name')
    
    ti = kwargs['ti']
    temp_filepath = ti.xcom_pull(task_ids='parse_document')
    
    with open(temp_filepath, 'r', encoding='utf-8') as f:
        full_text = f.read()
        
    # 1. Chunking
    chunks = []
    chunk_size = 1000
    overlap = 200
    
    start = 0
    while start < len(full_text):
        end = min(start + chunk_size, len(full_text))
        chunks.append(full_text[start:end].strip())
        if end == len(full_text):
            break
        start += (chunk_size - overlap)
        
    print(f"Generated {len(chunks)} chunks for index creation.")
    
    # 2. Embedding generation via local Ollama (nomic-embed-text)
    collection_id = f"doc_{uuid.uuid4().hex}"
    
    # Create Qdrant Collection
    qdrant_headers = {"Content-Type": "application/json"}
    qdrant_create_url = f"{QDRANT_URL}/collections/{collection_id}"
    create_body = {
        "vectors": {
            "size": 768, # nomic-embed-text dimension
            "distance": "Cosine"
        }
    }
    
    r = requests.put(qdrant_create_url, json=create_body, headers=qdrant_headers)
    r.raise_for_status()
    
    points = []
    # Loop chunks and embed
    for idx, chunk in enumerate(chunks):
        ollama_embed_url = f"{OLLAMA_URL}/api/embeddings"
        ollama_payload = {
            "model": "nomic-embed-text",
            "prompt": chunk
        }
        
        o_res = requests.post(ollama_embed_url, json=ollama_payload, timeout=20)
        o_res.raise_for_status()
        
        vector = o_res.json()["embedding"]
        
        points.append({
            "id": idx,
            "vector": vector,
            "payload": {
                "text": chunk,
                "chunk_index": idx,
                "document_name": file_name
            }
        })
        
    # Upsert points in batches to Qdrant
    batch_size = 20
    for k in range(0, len(points), batch_size):
        batch = points[k:k+batch_size]
        upsert_url = f"{QDRANT_URL}/collections/{collection_id}/points"
        requests.put(upsert_url, json={"points": batch}, headers=qdrant_headers).raise_for_status()
        
    print(f"Successfully upserted vectors for collection: {collection_id}")
    
    # Pass details to callback
    return {
        "collection_id": collection_id,
        "chunk_count": len(chunks)
    }

def notify_backend_success_fn(**kwargs):
    conf = kwargs['dag_run'].conf
    document_id = conf.get('document_id')
    
    ti = kwargs['ti']
    insights_path = ti.xcom_pull(task_ids='generate_insights')
    index_details = ti.xcom_pull(task_ids='embed_and_index')
    
    with open(insights_path, 'r', encoding='utf-8') as f:
        insights = json.load(f)
        
    # Call Webhook
    callback_url = f"{BACKEND_URL}/{document_id}/etl-complete"
    payload = {
        "vector_collection_id": index_details["collection_id"],
        "chunk_count": index_details["chunk_count"],
        "summary": insights.get("summary", ""),
        "suggested_questions": insights.get("suggestedQuestions", [])
    }
    
    print(f"Calling success webhook at: {callback_url}")
    r = requests.post(callback_url, json=payload, timeout=10)
    r.raise_for_status()
    
    # Clean up temp files
    temp_filepath = ti.xcom_pull(task_ids='parse_document')
    try:
        os.remove(temp_filepath)
        os.remove(insights_path)
        print("Cleaned up temporary workspace files successfully.")
    except Exception as e:
        print(f"Warning: Failed to clean up temp files: {e}")

def notify_backend_fail_fn(context):
    conf = context['dag_run'].conf
    document_id = conf.get('document_id')
    
    callback_url = f"{BACKEND_URL}/{document_id}/etl-fail"
    print(f"DAG failed! Calling failure webhook at: {callback_url}")
    try:
        requests.post(callback_url, timeout=10)
    except Exception as e:
        print(f"Critical: Failed to notify backend of ETL failure: {e}")

# Register failure callback on the DAG
dag.on_failure_callback = notify_backend_fail_fn

parse_task = PythonOperator(
    task_id='parse_document',
    python_callable=parse_document_fn,
    dag=dag,
)

insights_task = PythonOperator(
    task_id='generate_insights',
    python_callable=generate_insights_fn,
    dag=dag,
)

index_task = PythonOperator(
    task_id='embed_and_index',
    python_callable=embed_and_index_fn,
    dag=dag,
)

notify_task = PythonOperator(
    task_id='notify_backend_success',
    python_callable=notify_backend_success_fn,
    dag=dag,
)

# Define pipeline execution sequence: parse first, then insights & embeddings in parallel, finally notify backend
parse_task >> [insights_task, index_task] >> notify_task
