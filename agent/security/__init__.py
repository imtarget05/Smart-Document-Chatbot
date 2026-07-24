"""
Security utilities for the Smart Document Chatbot agent.

Modules:
    prompt_injection — heuristic detection of prompt-injection attacks.
"""

from .prompt_injection import (
    InjectionResult,
    detect_prompt_injection,
    sanitize_query,
)

__all__ = [
    "InjectionResult",
    "detect_prompt_injection",
    "sanitize_query",
]
