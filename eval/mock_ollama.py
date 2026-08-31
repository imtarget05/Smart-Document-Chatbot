#!/usr/bin/env python3
"""
Mock Ollama service for local evaluation and testing.
Simulates the Ollama HTTP API on port 11434 with deterministic responses
for Vietnamese legal document questions.
"""

import hashlib
import json
import random
import time
from datetime import datetime, timezone
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ─── App setup ───

app = FastAPI(title="Mock Ollama Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

EMBEDDING_DIM = 768
DEFAULT_MODEL = "llama3.2"
EMBED_MODEL = "nomic-embed-text"
AVAILABLE_MODELS = [DEFAULT_MODEL, EMBED_MODEL]


def deterministic_embedding(text: str, dim: int = EMBEDDING_DIM) -> list[float]:
    """Generate a deterministic pseudo-random embedding vector from input text."""
    seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
    rng = random.Random(seed)
    vec = [rng.uniform(-1.0, 1.0) for _ in range(dim)]
    norm = sum(x * x for x in vec) ** 0.5 or 1.0
    return [round(x / norm, 6) for x in vec]


def ollama_timings(prompt_tokens: int, eval_tokens: int) -> dict[str, int]:
    """Generate realistic Ollama timing fields in nanoseconds."""
    base = 1_000_000
    return {
        "total_duration": (prompt_tokens + eval_tokens) * base * 10,
        "load_duration": 50_000_000,
        "prompt_eval_count": prompt_tokens,
        "prompt_eval_duration": prompt_tokens * base,
        "eval_count": eval_tokens,
        "eval_duration": eval_tokens * base * 5,
    }


# ─── Request / Response models ───

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatOptions(BaseModel):
    temperature: Optional[float] = 0.3
    top_p: Optional[float] = 0.95
    num_predict: Optional[int] = 500


class ChatRequest(BaseModel):
    model: str = DEFAULT_MODEL
    messages: list[ChatMessage]
    options: Optional[ChatOptions] = None
    stream: bool = False
    think: Optional[bool] = False


class EmbeddingRequest(BaseModel):
    model: str = EMBED_MODEL
    prompt: str


# ─── Context-aware response generation ───

def extract_context_and_question(messages: list[ChatMessage]) -> tuple[str, str]:
    """Extract document context and user question from messages array.
    
    Handles two formats:
    1. Backend format: system=generic prompt, user=full prompt with context + question
    2. Direct format: system=context, user=question
    """
    system_content = ""
    user_content = ""

    for msg in messages:
        if msg.role == "system":
            system_content = msg.content
        elif msg.role == "user":
            user_content = msg.content

    # Check if user content contains document context (backend format)
    if "Context from the document:" in user_content or "context" in user_content.lower():
        # Extract context from user message
        context_parts = []
        question = user_content
        
        # Try to extract context sections
        if "Context from the document:" in user_content:
            parts = user_content.split("Context from the document:")
            if len(parts) > 1:
                context_and_question = parts[1]
                # Split by "User Question:" to separate context from question
                if "User Question:" in context_and_question:
                    cq_parts = context_and_question.split("User Question:")
                    context_parts.append(cq_parts[0].strip())
                    question = cq_parts[1].strip() if len(cq_parts) > 1 else ""
                else:
                    context_parts.append(context_and_question.strip())
        elif "Document context:" in user_content:
            parts = user_content.split("Document context:")
            if len(parts) > 1:
                context_parts.append(parts[1].strip())
        
        context = "\n".join(context_parts) if context_parts else system_content
        return context, question
    
    # Direct format: system contains context
    if system_content and len(system_content) > 50:
        return system_content, user_content
    
    # Fallback: use system as context
    return system_content, user_content


def generate_contextual_response(context: str, question: str) -> str:
    """Generate response based on document context."""
    if not context or len(context) < 20:
        return "Tôi không tìm thấy thông tin liên quan trong tài liệu."

    context_lower = context.lower()
    question_lower = question.lower()

    # Extract key terms from question (words longer than 3 chars)
    question_terms = [w for w in question_lower.split() if len(w) > 3]

    # Split context into sentences and find relevant ones
    sentences = context.replace(". ", ".\n").split("\n")
    relevant_sentences = []

    for sentence in sentences:
        sentence_lower = sentence.lower()
        # Check if sentence shares terms with question
        overlap = sum(1 for term in question_terms if term in sentence_lower)
        if overlap > 0:
            relevant_sentences.append(sentence.strip())

    if relevant_sentences:
        # Return the most relevant sentences
        answer = ". ".join(relevant_sentences[:3])
        if not answer.endswith("."):
            answer += "."
        return answer

    # Fallback: return first part of context
    return context[:300] + "..." if len(context) > 300 else context


# ─── Endpoints ───

@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/tags")
async def tags():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    models = []
    for name in AVAILABLE_MODELS:
        models.append(
            {
                "name": name,
                "model": name,
                "modified_at": now,
                "size": 4_661_224_676 if name == DEFAULT_MODEL else 274_322_112,
                "digest": hashlib.sha256(name.encode()).hexdigest()[:64],
                "details": {
                    "parent_model": "",
                    "format": "gguf",
                    "family": "llama" if "llama" in name else "nomic-bert",
                    "families": ["llama"] if "llama" in name else ["nomic-bert"],
                    "parameter_size": "3.2B" if name == DEFAULT_MODEL else "137M",
                    "quantization_level": "Q4_K_M",
                },
            }
        )
    return {"models": models}


@app.post("/api/chat")
async def chat(request: ChatRequest):
    if request.model not in AVAILABLE_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"model '{request.model}' not found",
        )

    # Extract context and question from messages
    context, user_message = extract_context_and_question(request.messages)

    if not user_message:
        raise HTTPException(status_code=400, detail="no user message found")

    # Generate response based on context
    if context and len(context) > 20:
        content = generate_contextual_response(context, user_message)
    else:
        content = "Tôi không tìm thấy thông tin liên quan trong tài liệu."

    prompt_tokens = len(user_message.split()) + len(context.split())
    eval_tokens = len(content.split())
    timings = ollama_timings(prompt_tokens, eval_tokens)

    return {
        "model": request.model,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "message": {"role": "assistant", "content": content},
        "done": True,
        "done_reason": "stop",
        **timings,
    }


@app.post("/api/embeddings")
async def embeddings(request: EmbeddingRequest):
    if request.model not in AVAILABLE_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"model '{request.model}' not found",
        )

    if not request.prompt:
        raise HTTPException(status_code=400, detail="prompt is required")

    vector = deterministic_embedding(request.prompt)
    prompt_tokens = len(request.prompt.split())

    return {
        "model": request.model,
        "embedding": vector,
        "total_duration": 25_000_000,
        "load_duration": 15_000_000,
        "prompt_eval_count": prompt_tokens,
        "prompt_eval_duration": prompt_tokens * 1_000_000,
    }


# ─── Entry point ───

if __name__ == "__main__":
    print("🦙 Mock Ollama service starting on http://localhost:11434")
    print("   Available models: llama3.2, nomic-embed-text")
    print("   Endpoints: /api/chat, /api/embeddings, /api/tags, /api/health")
    uvicorn.run(app, host="0.0.0.0", port=11434)
