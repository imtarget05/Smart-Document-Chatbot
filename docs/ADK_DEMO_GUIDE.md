# ADK Demo Guide

## Run locally

```bash
cd agent
python3 -m pip install -r requirements.txt
python3 -m pytest -q tests/test_adk_agent.py tests/test_adk_runtime.py tests/test_adk_endpoint.py tests/test_adk_trace.py
```

## Demo endpoint

```bash
curl -X POST http://127.0.0.1:8000/agent/adk/demo \
  -H 'Content-Type: application/json' \
  -d '{"user_request":"Summarize the report","document_name":"demo.pdf"}'
```

## What the demo shows

- An ADK-style agent spec
- A runnable workflow with 5 steps
- Logging and trace metadata for each step
- A minimal FastAPI endpoint for the video demo
