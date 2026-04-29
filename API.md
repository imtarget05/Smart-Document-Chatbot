# API Documentation

## Base URL
```
http://localhost:8080/api
```

## Authentication
Currently no authentication required. (JWT to be implemented)

---

## Endpoints

### 📄 Document Management

#### Upload Document
```http
POST /documents/upload
Content-Type: multipart/form-data

Body: form-data
  - file: <PDF/Word/TXT file>

Response: 200 OK
{
  "success": true,
  "message": "Document uploaded successfully",
  "documentId": 1,
  "fileName": "example.pdf"
}
```

#### Get All Documents
```http
GET /documents

Response: 200 OK
[
  {
    "id": 1,
    "fileName": "example.pdf",
    "fileType": "pdf",
    "fileSize": 102400,
    "chunkCount": 5,
    "createdAt": "2024-01-15T10:30:00",
    "updatedAt": "2024-01-15T10:30:00"
  }
]
```

#### Get Document Details
```http
GET /documents/{id}

Response: 200 OK
{
  "id": 1,
  "fileName": "example.pdf",
  "fileType": "pdf",
  "fileSize": 102400,
  "chunkCount": 5,
  "createdAt": "2024-01-15T10:30:00",
  "updatedAt": "2024-01-15T10:30:00"
}
```

#### Delete Document
```http
DELETE /documents/{id}

Response: 200 OK
"Document deleted successfully"
```

---

### 💬 Chat Management

#### Ask Question
```http
POST /chat/ask
Content-Type: application/json

Body:
{
  "sessionId": "uuid",
  "documentId": 1,
  "message": "What is the main topic?"
}

Response: 200 OK
{
  "id": 1,
  "sessionId": "uuid",
  "documentId": 1,
  "userMessage": "What is the main topic?",
  "aiResponse": "The main topic is...",
  "sourceChunks": "Chunk 1\n---\nChunk 2\n---\nChunk 3"
}
```

#### Get Chat History
```http
GET /chat/history/{sessionId}

Response: 200 OK
[
  {
    "id": 1,
    "sessionId": "uuid",
    "documentId": 1,
    "userMessage": "Question 1",
    "aiResponse": "Answer 1",
    "sourceChunks": "..."
  }
]
```

#### Get Chat History by Document
```http
GET /chat/history/{sessionId}/{documentId}

Response: 200 OK
[
  {
    "id": 1,
    "sessionId": "uuid",
    "documentId": 1,
    "userMessage": "Question 1",
    "aiResponse": "Answer 1",
    "sourceChunks": "..."
  }
]
```

#### Clear Chat History
```http
DELETE /chat/history/{sessionId}

Response: 200 OK
"Chat history cleared"
```

---

### 🔌 WebSocket

#### Connect
```
ws://localhost:8080/ws/chat
```

#### Send Message
```javascript
// StompJS
client.send("/app/chat/send", {}, JSON.stringify({
  sessionId: "uuid",
  documentId: 1,
  message: "Your question"
}));

// Receive
client.subscribe("/topic/messages", (msg) => {
  console.log(JSON.parse(msg.body));
});
```

---

## Error Responses

### 400 Bad Request
```json
{
  "error": "File is empty"
}
```

### 404 Not Found
```json
{
  "error": "Document not found"
}
```

### 413 Payload Too Large
```json
{
  "error": "File size exceeds maximum limit of 50MB"
}
```

### 500 Internal Server Error
```json
{
  "error": "An unexpected error occurred"
}
```

---

## Rate Limiting
- Not implemented yet (coming in future versions)

---

## Pagination
- Not implemented yet

---

## Examples

### Python
```python
import requests

# Upload document
files = {'file': open('document.pdf', 'rb')}
response = requests.post('http://localhost:8080/api/documents/upload', files=files)
doc_id = response.json()['documentId']

# Ask question
payload = {
    'sessionId': 'my-session-123',
    'documentId': doc_id,
    'message': 'What is this document about?'
}
response = requests.post('http://localhost:8080/api/chat/ask', json=payload)
print(response.json()['aiResponse'])
```

### JavaScript/Node.js
```javascript
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

async function uploadDocument() {
  const form = new FormData();
  form.append('file', fs.createReadStream('document.pdf'));
  
  const response = await axios.post(
    'http://localhost:8080/api/documents/upload',
    form,
    { headers: form.getHeaders() }
  );
  
  return response.data.documentId;
}

async function askQuestion(sessionId, documentId, message) {
  const response = await axios.post(
    'http://localhost:8080/api/chat/ask',
    { sessionId, documentId, message }
  );
  
  return response.data.aiResponse;
}
```

### cURL
```bash
# Upload document
curl -X POST \
  -F "file=@document.pdf" \
  http://localhost:8080/api/documents/upload

# Ask question
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"sessionId":"123","documentId":1,"message":"What is this?"}' \
  http://localhost:8080/api/chat/ask

# Get chat history
curl http://localhost:8080/api/chat/history/123
```

---

## Response Codes

| Code | Meaning |
|------|---------|
| 200 | OK - Request succeeded |
| 201 | Created - Resource created |
| 400 | Bad Request - Invalid input |
| 404 | Not Found - Resource doesn't exist |
| 413 | Payload Too Large - File too big |
| 500 | Internal Server Error |

---

## Future API Enhancements

- [ ] JWT Authentication
- [ ] Pagination for chat history
- [ ] Filtering and sorting
- [ ] User profiles
- [ ] Document sharing
- [ ] API rate limiting
- [ ] Webhook events
- [ ] Batch operations

---

For more details, check [README.md](README.md)
