# n8n AI Workflow Automation

This directory contains n8n workflow demonstrations for the Smart Document Chatbot.

## Workflows

### 1. Document Ingestion Pipeline (`01-document-ingestion.json`)
Automates document processing when a new document is uploaded.

**Flow:** Webhook → Upload to Backend → Wait → Get Chunks → Save Analytics → Respond

**Use case:** Trigger external systems when documents are processed.

### 2. AI Chat with Confidence Routing (`02-ai-chat-automation.json`)
Routes chat questions based on AI confidence score.

**Flow:** Webhook → Call Chat API → Check Confidence → Return Answer OR Escalate to Human

**Use case:** Auto-answer high-confidence questions, escalate low-confidence to human review.

### 3. Scheduled Document Summary (`03-scheduled-summary.json`)
Daily automated summary generation for all documents.

**Flow:** Schedule (9am) → Get Documents → Generate Summary → Save to DB

**Use case:** Daily digest of new/updated documents.

## Setup

1. Start n8n:
   ```bash
   docker compose -f docker/docker-compose.yml up -d n8n
   ```

2. Open n8n: http://localhost:5678

3. Import workflows:
   - Click "Add Workflow" → "Import from File"
   - Select each JSON file

4. Configure credentials:
   - Postgres: `host=postgres, port=5432, user=postgres, password=postgres, database=smartdoc`
   - Backend API: `http://localhost:8080/api`

5. Activate workflows (toggle "Active" switch)

## Architecture

```
n8n Workflow → Backend API (Spring Boot) → LLM Router → Ollama/Cloudflare
                     ↓
               PostgreSQL (analytics, escalations, summaries)
```

## Demo Workflow

For interview demo, use Workflow 2 (AI Chat with Confidence Routing):

1. Send POST to `http://localhost:5678/webhook/chat-question`:
   ```json
   {
     "token": "your-jwt-token",
     "csrf": "your-csrf-token",
     "sessionId": "demo-123",
     "documentId": 2,
     "message": "Điều 7 quy định gì?"
   }
   ```

2. If confidence = "high" → returns answer immediately
3. If confidence = "low" → saves to escalation_queue for human review
