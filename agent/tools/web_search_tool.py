"""
Web search tool using Tavily API.
Falls back gracefully if TAVILY_API_KEY is not configured.
"""

import logging
from typing import Any, Dict, List

from settings import settings

logger = logging.getLogger(__name__)


class TavilySearch:
    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        if not settings.tavily_api_key:
            logger.warning("TAVILY_API_KEY not configured – web search skipped")
            return []

        try:
            from tavily import TavilyClient
            client  = TavilyClient(api_key=settings.tavily_api_key)
            # Run synchronous Tavily call in a thread pool to keep async
            import asyncio
            loop    = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: client.search(query=query, max_results=max_results, search_depth="advanced"),
            )
            return results.get("results", [])
        except Exception as exc:
            logger.warning("Tavily search error: %s", exc)
            return []
