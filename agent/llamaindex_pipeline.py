"""
Lightweight LlamaIndex RAG pipeline.

Provides an alternative document ingestion and querying pipeline using LlamaIndex.
Falls back gracefully if llama-index is not installed.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    from llama_index.core import (
        SimpleDirectoryReader,
        StorageContext,
        VectorStoreIndex,
        Settings as LlamaSettings,
    )
    from llama_index.core.query_engine import RetrieverQueryEngine
    from llama_index.core.retrievers import VectorIndexRetriever
    from llama_index.core.vector_stores.types import VectorStoreQueryMode
    from llama_index.llms.ollama import Ollama as LlamaOllama
    from llama_index.embeddings.ollama import OllamaEmbedding

    LLAMAINDEX_AVAILABLE = True
except ImportError:
    LLAMAINDEX_AVAILABLE = False
    logger.warning("llama-index not installed. LlamaIndexRag will use fallback mode.")


class LlamaIndexRag:
    """LlamaIndex-based RAG pipeline for document ingestion and querying.

    Loads documents from a directory, builds a vector store index, and supports
    hybrid search when available.
    """

    def __init__(
        self,
        docs_dir: str = "./docs",
        llm_model: str = "llama3.1",
        llm_base_url: str = "http://localhost:11434",
        embedding_model: str = "nomic-embed-text",
        collection_name: str = "smart_doc_chatbot",
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        qdrant_api_key: str = "",
        use_qdrant: bool = False,
    ) -> None:
        self.docs_dir = docs_dir
        self.llm_model = llm_model
        self.llm_base_url = llm_base_url
        self.embedding_model = embedding_model
        self.collection_name = collection_name
        self.qdrant_host = qdrant_host
        self.qdrant_port = qdrant_port
        self.qdrant_api_key = qdrant_api_key
        self.use_qdrant = use_qdrant
        self._index: Optional[Any] = None
        self._query_engine: Optional[Any] = None
        self._fallback_mode = not LLAMAINDEX_AVAILABLE

    def _configure_settings(self) -> None:
        """Configure LlamaIndex global settings."""
        if self._fallback_mode:
            return
        LlamaSettings.llm = LlamaOllama(
            model=self.llm_model,
            base_url=self.llm_base_url,
        )
        LlamaSettings.embed_model = OllamaEmbedding(
            model_name=self.embedding_model,
            base_url=self.llm_base_url,
        )

    def _build_qdrant_store(self) -> Any:
        """Build a Qdrant vector store."""
        from llama_index.vector_stores.qdrant import QdrantVectorStore
        from qdrant_client import QdrantClient

        client = QdrantClient(
            host=self.qdrant_host,
            port=self.qdrant_port,
            api_key=self.qdrant_api_key or None,
        )
        return QdrantVectorStore(client=client, collection_name=self.collection_name)

    def load_documents(self) -> list[Any]:
        """Load documents from the configured directory."""
        if self._fallback_mode:
            logger.info("Fallback mode: returning empty document list.")
            return []
        if not os.path.isdir(self.docs_dir):
            logger.warning("Documents directory not found: %s", self.docs_dir)
            return []
        reader = SimpleDirectoryReader(self.docs_dir)
        return reader.load_data()

    def build_index(self, documents: Optional[list[Any]] = None) -> None:
        """Build the vector store index from documents."""
        if self._fallback_mode:
            logger.info("Fallback mode: skipping index build.")
            return
        self._configure_settings()
        docs = documents or self.load_documents()
        if not docs:
            logger.warning("No documents to index.")
            return

        if self.use_qdrant:
            vector_store = self._build_qdrant_store()
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            self._index = VectorStoreIndex.from_documents(
                docs, storage_context=storage_context
            )
        else:
            self._index = VectorStoreIndex.from_documents(docs)

        self._query_engine = self._index.as_query_engine(
            vector_store_query_mode=VectorStoreQueryMode.HYBRID
            if hasattr(VectorStoreQueryMode, "HYBRID")
            else VectorStoreQueryMode.DEFAULT
        )
        logger.info("Index built successfully with %d documents.", len(docs))

    def query(self, question: str) -> str:
        """Query the index and return the answer."""
        if self._fallback_mode:
            return (
                "LlamaIndex is not installed. Install with: "
                "pip install llama-index llama-index-vector-stores-qdrant"
            )
        if self._query_engine is None:
            self.build_index()
        if self._query_engine is None:
            return "No documents indexed. Cannot answer the question."
        response = self._query_engine.query(question)
        return str(response)

    @property
    def is_available(self) -> bool:
        """Check if LlamaIndex is available."""
        return LLAMAINDEX_AVAILABLE

    @property
    def is_ready(self) -> bool:
        """Check if the index is built and ready for queries."""
        return self._index is not None
