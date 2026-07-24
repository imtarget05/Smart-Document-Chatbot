"""
Qdrant Hybrid Search Tool - Phase 1.

Combines:
  1. Semantic search  - Qdrant cosine similarity via nomic-embed-text embeddings
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
from typing import Any, Dict, List, Optional

import httpx
from rank_bm25 import BM25Okapi

from settings import settings

logger = logging.getLogger(__name__)

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
        self._http = httpx.AsyncClient(timeout=30)

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
    # Semantic search
    # ------------------------------------------------------------------
    async def _semantic_search(
        self, query: str, collection_id: str, top_k: int
    ) -> List[Dict[str, Any]]:
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
            resp = await self._http.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            points = data.get("result", [])
        except Exception as exc:
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
    # Embedding
    # ------------------------------------------------------------------
    async def _embed(self, text: str) -> Optional[List[float]]:
        try:
            resp = await self._http.post(
                self._embed_url,
                json={"model": self._embed_model, "prompt": text},
            )
            resp.raise_for_status()
            return resp.json().get("embedding", [])
        except Exception as exc:
            logger.error("Embedding failed: %s", exc)
            return None
