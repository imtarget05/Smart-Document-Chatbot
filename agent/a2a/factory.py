"""
A2A Factory — register all existing agents into the A2AProtocolHub.
Creates AgentCards for every agent in the system and registers their handlers.
"""

import logging
from typing import Callable, Dict, Optional

from a2a.protocol import A2AProtocolHub, AgentCard

logger = logging.getLogger(__name__)


def create_default_hub() -> A2AProtocolHub:
    """
    Create an A2AProtocolHub pre-populated with all existing agents.

    Returns:
        A2AProtocolHub with all agents registered
    """
    hub = A2AProtocolHub()
    return hub


def register_rag_agent(hub: A2AProtocolHub, handler: Optional[Callable] = None) -> None:
    """Register the RAG agent for document Q&A."""
    hub.register_agent(
        AgentCard(
            agent_id="rag_agent",
            name="RAG Agent",
            description="Answer questions from document context with RAG pipeline",
            capabilities=["rag", "qa", "document"],
            version="2.0.0",
            max_concurrent_tasks=5,
        ),
        handler=handler,
    )


def register_report_agent(
    hub: A2AProtocolHub, handler: Optional[Callable] = None
) -> None:
    """Register the Report agent for PDF/text generation."""
    hub.register_agent(
        AgentCard(
            agent_id="report_agent",
            name="Report Agent",
            description="Generate structured PDF/text reports from documents",
            capabilities=["report", "pdf", "summary"],
            version="1.0.0",
        ),
        handler=handler,
    )


def register_research_agent(
    hub: A2AProtocolHub, handler: Optional[Callable] = None
) -> None:
    """Register the Research agent for web search."""
    hub.register_agent(
        AgentCard(
            agent_id="research_agent",
            name="Research Agent",
            description="Perform web research with Tavily and synthesize answers",
            capabilities=["research", "web_search", "news"],
            version="1.0.0",
        ),
        handler=handler,
    )


def register_comparator_agent(
    hub: A2AProtocolHub, handler: Optional[Callable] = None
) -> None:
    """Register the Comparator agent for document comparison."""
    hub.register_agent(
        AgentCard(
            agent_id="comparator_agent",
            name="Comparator Agent",
            description="Compare documents side-by-side on a given topic",
            capabilities=["compare", "diff", "side-by-side"],
            version="1.0.0",
        ),
        handler=handler,
    )


def register_action_agent(
    hub: A2AProtocolHub, handler: Optional[Callable] = None
) -> None:
    """Register the Action agent for email/Jira/webhook execution."""
    hub.register_agent(
        AgentCard(
            agent_id="action_agent",
            name="Action Agent",
            description="Execute real-world actions: email, Jira, Notion, webhook",
            capabilities=["action", "email", "jira", "webhook"],
            version="1.0.0",
        ),
        handler=handler,
    )


def register_engineering_agent(
    hub: A2AProtocolHub, handler: Optional[Callable] = None
) -> None:
    """Register the Engineering Analysis agent for 8D reports."""
    hub.register_agent(
        AgentCard(
            agent_id="engineering_agent",
            name="Engineering Analysis Agent",
            description="Analyze test reports, failures, root-cause with 8D framework",
            capabilities=["engineering", "8d", "root_cause", "test_report"],
            version="1.0.0",
        ),
        handler=handler,
    )


def register_cskh_agent(
    hub: A2AProtocolHub, handler: Optional[Callable] = None
) -> None:
    """Register the CSKH agent for customer service."""
    hub.register_agent(
        AgentCard(
            agent_id="cskh_agent",
            name="CSKH Agent",
            description="Vietnamese-English customer service for Smart Shoes Vietnam",
            capabilities=["cskh", "customer_service", "product_consultation"],
            version="1.0.0",
        ),
        handler=handler,
    )


def register_orchestrator_agent(
    hub: A2AProtocolHub, handler: Optional[Callable] = None
) -> None:
    """Register the Orchestrator agent for intent routing."""
    hub.register_agent(
        AgentCard(
            agent_id="orchestrator",
            name="Orchestrator Agent",
            description="Route user queries to the appropriate specialist agent",
            capabilities=["routing", "intent_detection", "planning"],
            version="2.0.0",
        ),
        handler=handler,
    )


def register_finance_agent(
    hub: A2AProtocolHub, handler: Optional[Callable] = None
) -> None:
    """Register the Finance agent for stock/financial analysis."""
    hub.register_agent(
        AgentCard(
            agent_id="finance_agent",
            name="Finance Agent",
            description="Technical analysis (SMA, RSI, MACD), portfolio analysis",
            capabilities=["finance", "stock", "technical_analysis", "investment"],
            version="1.0.0",
        ),
        handler=handler,
    )


def register_code_agent(
    hub: A2AProtocolHub, handler: Optional[Callable] = None
) -> None:
    """Register the Code agent for programming tasks."""
    hub.register_agent(
        AgentCard(
            agent_id="code_agent",
            name="Code Agent",
            description="Write, debug, and refactor code",
            capabilities=["code", "debug", "refactor"],
            version="1.0.0",
        ),
        handler=handler,
    )


def register_summarizer_agent(
    hub: A2AProtocolHub, handler: Optional[Callable] = None
) -> None:
    """Register the Summarizer agent."""
    hub.register_agent(
        AgentCard(
            agent_id="summarizer_agent",
            name="Summarizer Agent",
            description="Summarize long documents and conversations",
            capabilities=["summarize", "condense"],
            version="1.0.0",
        ),
        handler=handler,
    )


def register_ingestion_agent(
    hub: A2AProtocolHub, handler: Optional[Callable] = None
) -> None:
    """Register the Ingestion agent for document processing."""
    hub.register_agent(
        AgentCard(
            agent_id="ingestion_agent",
            name="Ingestion Agent",
            description="Validate, parse, and index documents into Qdrant",
            capabilities=["ingestion", "indexing", "parsing"],
            version="1.0.0",
        ),
        handler=handler,
    )


def register_embedding_agent(
    hub: A2AProtocolHub, handler: Optional[Callable] = None
) -> None:
    """Register the Embedding agent."""
    hub.register_agent(
        AgentCard(
            agent_id="embedding_agent",
            name="Embedding Agent",
            description="Generate vector embeddings for text",
            capabilities=["embedding", "vectorize"],
            version="1.0.0",
        ),
        handler=handler,
    )


def register_all_agents(
    hub: A2AProtocolHub,
    handlers: Optional[Dict[str, Callable]] = None,
) -> None:
    """
    Register ALL agents into the hub.

    Args:
        hub: The A2AProtocolHub instance
        handlers: Optional dict of {agent_id: handler_function}
    """
    handlers = handlers or {}

    register_rag_agent(hub, handlers.get("rag_agent"))
    register_report_agent(hub, handlers.get("report_agent"))
    register_research_agent(hub, handlers.get("research_agent"))
    register_comparator_agent(hub, handlers.get("comparator_agent"))
    register_action_agent(hub, handlers.get("action_agent"))
    register_engineering_agent(hub, handlers.get("engineering_agent"))
    register_cskh_agent(hub, handlers.get("cskh_agent"))
    register_orchestrator_agent(hub, handlers.get("orchestrator"))
    register_finance_agent(hub, handlers.get("finance_agent"))
    register_code_agent(hub, handlers.get("code_agent"))
    register_summarizer_agent(hub, handlers.get("summarizer_agent"))
    register_ingestion_agent(hub, handlers.get("ingestion_agent"))
    register_embedding_agent(hub, handlers.get("embedding_agent"))

    logger.info(
        f"[A2AFactory] Registered {len(hub.discover_all())} agents into A2AProtocolHub"
    )
