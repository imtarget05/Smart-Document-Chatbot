# Smart-Document-Chatbot - Data Flow Architecture

## Project Overview
- **Description**: Self-hosted RAG system for document Q&A with context-aware answers
- **Language Composition**: Java (59%) | JavaScript (21.2%) | Shell (9.9%) | Makefile (6.8%) | CSS (2.4%) | HTML (0.7%)
- **Architecture**: Retrieval-Augmented Generation (RAG) powered chatbot

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│            SMART-DOCUMENT-CHATBOT (RAG System)              │
└─────────────────────────────────────────────────────────────┘

INPUT LAYER
    │
    ├─ User Documents
    │   ├─ PDF Files
    │   ├─ Text Files
    │   ├─ Word Documents
    │   └─ Other Formats
    │
    ├─ User Queries
    │   └─ Chat Messages
    │
    ▼

DOCUMENT INGESTION (Java - 59%)
    │
    ├─ File Upload Handler
    ├─ Document Parser
    │   ├─ Extract Text
    │   ├─ Metadata Extraction
    │   └─ Content Validation
    │
    ▼

EMBEDDING & INDEXING (Java + Shell Scripts)
    │
    ├─ Text Chunking
    │   ├─ Split into Chunks
    │   └─ Overlap Management
    │
    ├─ Vector Embedding Generation
    │   └─ Embedding Model Processing
    │
    ├─ Vector Database Indexing
    │   ├─ Store Vectors
    │   ├─ Create Indices
    │   └─ Optimize Retrieval
    │
    ▼

QUERY PROCESSING (Java)
    │
    ├─ Query Embedding Generation
    ├─ Semantic Search
    │   └─ Similarity Matching
    │
    ▼

RETRIEVAL AUGMENTED GENERATION (RAG Pipeline)
    │
    ├─ Retrieve Relevant Documents
    │   ├─ Vector Similarity Search
    │   ├─ Rank by Relevance
    │   └─ Select Top-K Documents
    │
    ├─ Context Assembly
    │   └─ Combine Retrieved + Query
    │
    ├─ LLM Generation
    │   └─ Generate Context-Aware Response
    │
    ▼

RESPONSE PROCESSING (Java + JavaScript)
    │
    ├─ Response Formatting
    ├─ Citation Management
    │   └─ Link to Source Documents
    │
    ├─ Post-Processing
    │   └─ Quality Checks
    │
    ▼

FRONTEND LAYER (JavaScript - 21.2% + HTML - 0.7% + CSS - 2.4%)
    │
    ├─ Chat Interface
    ├─ Document Upload UI
    ├─ Conversation Display
    ├─ Source Highlighting
    └─ Response Rendering

BACKEND API (Java - 59%)
    │
    ├─ REST Endpoints
    ├─ Session Management
    ├─ Authentication
    └─ Error Handling

BUILD & DEPLOYMENT (Shell - 9.9%, Makefile - 6.8%)
    │
    ├─ Build Scripts
    ├─ Container Orchestration
    ├─ Service Management
    └─ Deployment Automation

STORAGE LAYER
    │
    ├─ Document Store
    ├─ Vector Database
    ├─ Chat History
    └─ User Sessions
```

## Technology Stack
- **Backend Logic**: Java (59%)
- **Frontend Interaction**: JavaScript (21.2%)
- **DevOps/Build**: Shell (9.9%) + Makefile (6.8%)
- **Styling**: CSS (2.4%)
- **Markup**: HTML (0.7%)

## Key Data Transformations
1. Raw Documents → Parsed Content
2. Content → Text Chunks with Overlap
3. Chunks → Vector Embeddings
4. Query → Query Embedding
5. Query Embedding → Retrieved Document IDs
6. Retrieved Docs + Query → LLM Context
7. Context → Generated Response
8. Response → Formatted & Cited Answer
