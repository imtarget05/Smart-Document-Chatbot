"""
Qdrant Hybrid Search Tool - Phase 1.

Combines:
  1. Semantic search  - Qdrant cosine similarity via @cf/baai/bge-base-en-v1.5 embeddings
  2. BM25 keyword     - rank-bm25 scored against the semantic result subset
  3. RRF fusion       - Reciprocal Rank Fusion merges both ranked lists

The combined score is more robust than either approach alone,
especially for short/keyword-heavy queries.

Scalability note (issue #16):
    BM25 is applied ONLY to the semantic search results (top_k * 3), NOT to
    the entire corpus. This keeps the BM25 step O(m) where m = top_k * 3,
    making it safe for corpora > 100k chunks. For a full-corpus BM25 search,
    use a dedicated BM25 backend (e.g., Elasticsearch/OpenSearch) or Qdrant's
    built-in sparse vector support.
"""

import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional

import httpx
from rank_bm25 import BM25Okapi
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log

from settings import settings

logger = logging.getLogger(__name__)

# ── Simple circuit breaker for Qdrant (no extra dependency) ──
class _CircuitBreaker:
    def __init__(self, name: str, fail_max: int = 5, reset_timeout: float = 30.0):
        self.name = name
        self.fail_max = fail_max
        self.reset_timeout = reset_timeout
        self._failures = 0
        self._state = "closed"  # closed | open | half_open
        self._opened_at: Optional[float] = None

    def _emit(self):
        try:
            from metrics import circuit_breaker_state
            m = {"closed": 0, "half_open": 1, "open": 2}.get(self._state, 0)
            circuit_breaker_state.labels(agent_id=self.name).set(m)
        except Exception:
            pass

    def can_execute(self) -> bool:
        if self._state == "closed":
            return True
        if self._state == "open":
            if time.monotonic() - (self._opened_at or 0) >= self.reset_timeout:
                self._state = "half_open"
                self._emit()
                return True
            return False
        return True  # half_open: allow one trial

    def record_success(self):
        self._failures = 0
        if self._state != "closed":
            self._state = "closed"
            self._emit()

    def record_failure(self):
        self._failures += 1
        try:
            from metrics import circuit_breaker_failures
            circuit_breaker_failures.labels(agent_id=self.name).inc()
        except Exception:
            pass
        if self._state == "half_open" or self._failures >= self.fail_max:
            self._state = "open"
            self._opened_at = time.monotonic()
            self._emit()
            logger.warning("Circuit breaker OPEN for %s after %d failures", self.name, self._failures)

_qdrant_breaker = _CircuitBreaker("qdrant", fail_max=5, reset_timeout=30)
_embed_breaker = _CircuitBreaker("qdrant_embed", fail_max=5, reset_timeout=30)

# Optional Redis cache for RAG queries.
# Issue #48: Previously, a Redis import failure was silently swallowed and
# _redis_client was set to None with no log. Now we log a warning so operators
# know caching is disabled.
_redis_client = None
if getattr(settings, "redis_url", None):
    try:
        import redis

        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        logger.info("RAG Redis cache enabled: %s", settings.redis_url)
    except ImportError:
        logger.warning(
            "redis package not installed - RAG query caching disabled. "
            "Install with: pip install redis"
        )
    except Exception as exc:
        logger.warning(
            "RAG Redis cache init failed (%s) - caching disabled. "
            "Queries will hit Qdrant directly.",
            exc,
        )
else:
    logger.info("REDIS_URL not set - RAG query caching disabled.")


def _cache_key(query: str, collection_id: str, top_k: int) -> str:
    h = hashlib.sha256(f"{query}:{collection_id}:{top_k}".encode()).hexdigest()[:16]
    return f"rag_cache:{h}"


def _tokenize(text: str) -> List[str]:
    """Simple whitespace + lower-case tokeniser for BM25."""
    return text.lower().split()


def _rrf_score(rank: int, k: int) -> float:
    """Reciprocal Rank Fusion score."""
    return 1.0 / (k + rank + 1)


class QdrantHybridSearch:
    """Async Qdrant wrapper with hybrid BM25 + semantic search."""

    def __init__(self):
        self._base_url = f"http://{settings.qdrant_host}:{settings.qdrant_port}"
        self._api_key = settings.qdrant_api_key
        self._embed_url = f"{settings.llm_base_url}/api/embeddings"
        self._embed_model = settings.llm_embedding_model
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=5.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def hybrid_search(
        self,
        query: str,
        collection_id: str,
        top_k: int = 5,
        use_bm25: bool = True,
        rrf_k: int = 60,
    ) -> List[Dict[str, Any]]:
        """
        Returns a list of chunk dicts sorted by hybrid score (descending).
        Each dict has keys: text, document_name, score, chunk_index.

        rrf_k controls the RRF constant: higher values = more weight to BM25 ranking.
        """
        # Try Redis cache first
        cache_ttl = getattr(settings, "rag_cache_ttl_sec", 300)
        if _redis_client:
            try:
                ck = _cache_key(query, collection_id, top_k)
                cached = _redis_client.get(ck)
                if cached:
                    logger.debug("RAG cache hit for query: %s", query[:40])
                    return json.loads(cached)
            except Exception as exc:
                logger.warning("RAG cache read failed: %s", exc)

        # 1. Semantic search via Qdrant
        semantic_results = await self._semantic_search(
            query, collection_id, top_k=top_k * 3
        )
        if not semantic_results:
            return []

        if not use_bm25 or len(semantic_results) <= 2:
            return semantic_results[:top_k]

        # 2. BM25 on the semantic result corpus (avoid extra Qdrant scroll)
        # NOTE: This is O(m) where m = len(semantic_results) = top_k * 3, NOT O(n)
        # over the full corpus. Safe for large corpora (issue #16).
        corpus = [r["text"] for r in semantic_results]
        bm25 = BM25Okapi([_tokenize(t) for t in corpus])
        bm25_scores = bm25.get_scores(_tokenize(query))

        # 3. RRF fusion
        # Build rank maps
        semantic_ranks = {r["text"]: i for i, r in enumerate(semantic_results)}
        bm25_indexed = sorted(enumerate(bm25_scores), key=lambda x: x[1], reverse=True)
        bm25_ranks = {
            semantic_results[i]["text"]: rank
            for rank, (i, _) in enumerate(bm25_indexed)
        }

        fused: Dict[str, float] = {}
        for chunk in semantic_results:
            text = chunk["text"]
            sem_rank = semantic_ranks.get(text, len(semantic_results))
            bm25_rank = bm25_ranks.get(text, len(semantic_results))
            fused[text] = _rrf_score(sem_rank, rrf_k) + _rrf_score(bm25_rank, rrf_k)

        # 4. Re-sort by fused score and normalise
        max_fused = max(fused.values()) or 1.0
        results_out: List[Dict[str, Any]] = []
        for chunk in semantic_results:
            merged = dict(chunk)
            merged["score"] = fused.get(chunk["text"], 0.0) / max_fused
            results_out.append(merged)

        results_out.sort(key=lambda x: x["score"], reverse=True)
        final = results_out[:top_k]

        # Write to Redis cache
        if _redis_client:
            try:
                ck = _cache_key(query, collection_id, top_k)
                _redis_client.setex(ck, cache_ttl, json.dumps(final))
            except Exception as exc:
                logger.warning("RAG cache write failed: %s", exc)

        return final

    # ------------------------------------------------------------------
    # Semantic search — with retry + circuit breaker
    # ------------------------------------------------------------------
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError)),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
        reraise=True,
    )
    async def _semantic_search_inner(
        self, url: str, payload: Dict[str, Any], headers: Dict[str, str]
    ):
        resp = await self._http.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()

    async def _semantic_search(
        self, query: str, collection_id: str, top_k: int
    ) -> List[Dict[str, Any]]:
        if not _qdrant_breaker.can_execute():
            logger.warning("Qdrant circuit OPEN — skipping search for %s", collection_id)
            return []
        vector = await self._embed(query)
        if not vector:
            return []

        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["api-key"] = self._api_key

        payload = {
            "vector": vector,
            "limit": top_k,
            "with_payload": True,
        }
        url = f"{self._base_url}/collections/{collection_id}/points/search"
        try:
            data = await self._semantic_search_inner(url, payload, headers)
            points = data.get("result", [])
            _qdrant_breaker.record_success()
        except Exception as exc:
            _qdrant_breaker.record_failure()
            logger.warning(
                "Qdrant search failed for collection %s: %s", collection_id, exc
            )
            return []

        results = []
        for p in points:
            pl = p.get("payload", {})
            results.append(
                {
                    "text": pl.get("text", ""),
                    "document_name": pl.get("document_name", collection_id),
                    "chunk_index": pl.get("chunk_index", 0),
                    "source_type": pl.get("source_type", "document"),
                    "source": pl.get("source", ""),
                    "external_id": pl.get("external_id", ""),
                    "score": p.get("score", 0.0),
                }
            )
        return results

    # ------------------------------------------------------------------
    # Embedding — with retry + circuit breaker
    # ------------------------------------------------------------------
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError)),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
        reraise=True,
    )
    async def _embed_inner(self, payload: Dict[str, Any]):
        resp = await self._http.post(self._embed_url, json=payload)
        resp.raise_for_status()
        return resp.json()

    async def _embed(self, text: str) -> Optional[List[float]]:
        if not _embed_breaker.can_execute():
            logger.warning("Embedding circuit OPEN — skipping embed")
            return None
        try:
            data = await self._embed_inner({"model": self._embed_model, "prompt": text})
            _embed_breaker.record_success()
            return data.get("embedding", [])
        except Exception as exc:
            _embed_breaker.record_failure()
            logger.error("Embedding failed: %s", exc)
            return None
