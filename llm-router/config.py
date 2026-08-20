"""
Configuration for the LLM Router service.
Handles model routing, complexity detection, and cost-aware decisions.
"""

# Model configuration - Sử dụng model đã cài sẵn trên Ollama
MODEL_CONFIG = {
    "primary": "qwen2.5:7b",      # Model chính - qwen2.5:7b đã cài sẵn (4.7GB)
    "fallback": "llama3.2:1b",    # Model rollback - llama3.2:1b (1.3GB - nhät nhẹ nhất)
    "embedding": "nomic-embed-text",  # Embedding model đã cài sẵn (274MB)
    
    # Routeing heuristics
    "complexity_threshold": 0.5,  # Ngưỡng phức tạp (0-1): dưới ngưỡng dùng model nhẹ, trên dùng model nặng
    "cost_priority": "balanced",  # "cheap", "quality", "auto"
    
    # Token limits
    "max_context_tokens": 8192,
    "max_response_tokens": 2048,
    
    # Runtime settings
    "ollama_base_url": "http://localhost:11434",
    "timeout_seconds": 30,
    "max_retries": 3,
}

# Legal domain specific settings
LEGAL_DOMAIN = {
    "complex_keywords": ["lawsuit", "contract", "liability", "negligence", "statute", "precedent", "jurisdiction"],
    "simple_keywords": ["what", "how", "where", "when", "who", "yes", "no"],
    "min_context_for_complex": 3,  # Số lượng tài liệu tối thiểu để coi là phức tạp
}

# Quality settings
QUALITY_SETTINGS = {
    "min_quality_score": 0.7,
    "max_latency_seconds": 5.0,
    "enable_circuit_breaker": True,
    "circuit_breaker_threshold": 5,  # Số lượng thất bại liên tiếp trước khi tắt model
}