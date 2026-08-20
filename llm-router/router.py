"""
Routing logic for selecting the appropriate LLM model based on
complexity, cost, and domain requirements.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import MODEL_CONFIG, LEGAL_DOMAIN, QUALITY_SETTINGS


def determine_model(user_query: str, conversation_history: list = None) -> str:
    """
    Determine which model to use based on query complexity and domain.
    
    Args:
        user_query: The user's query string
        conversation_history: Previous conversation turns
        
    Returns:
        Model name to use (e.g., "qwen2.5:7b", "llama3.2:1b")
    """
    # Analyze query complexity
    query_lower = user_query.lower()
    
    # Count complex keywords
    complex_count = sum(1 for kw in LEGAL_DOMAIN["complex_keywords"] if kw in query_lower)
    simple_count = sum(1 for kw in LEGAL_DOMAIN["simple_keywords"] if kw in query_lower)
    
    # Determine if query is complex based on:
    # - Keyword matches
    # - Number of documents/retrievals needed (if available)
    # - Query length and syntactic complexity
    
    is_complex = (
        complex_count > simple_count 
        or (complex_count >= LEGAL_DOMAIN["min_context_for_complex"])
    )
    
    # Select model based on complexity and cost priority
    if is_complex:
        # Complex queries use the primary model for better quality
        selected = MODEL_CONFIG["primary"]
    else:
        # Simple queries can use cost-effective routing
        if MODEL_CONFIG["cost_priority"] == "cheap":
            selected = MODEL_CONFIG["fallback"]
        elif MODEL_CONFIG["cost_priority"] == "quality":
            selected = MODEL_CONFIG["primary"]
        else:  # balanced
            # 70% primary, 30% fallback depending on latency/quality history
            selected = MODEL_CONFIG["primary"]
    
    return selected


def should_use_circuit_breaker(failure_count: int, settings=None) -> bool:
    """
    Determine if circuit breaker should be triggered.
    
    Args:
        failure_count: Number of consecutive failures
        settings: Quality settings dict
        
    Returns:
        True if circuit breaker should open
    """
    settings = settings or QUALITY_SETTINGS
    return failure_count >= settings["circuit_breaker_threshold"]


def check_quality_threshold(latency: float, quality_score: float, settings=None) -> bool:
    """
    Check if the response meets quality thresholds.
    
    Args:
        latency: Response latency in seconds
        quality_score: Model quality score (0-1)
        settings: Quality settings dict
        
    Returns:
        True if response meets quality requirements
    """
    settings = settings or QUALITY_SETTINGS
    latency_ok = latency <= settings["max_latency_seconds"]
    quality_ok = quality_score >= settings["min_quality_score"]
    return latency_ok and quality_ok