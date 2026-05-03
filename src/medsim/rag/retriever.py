"""Retriever — formats vector-store hits into a single context string."""

from __future__ import annotations

import logging

from medsim.rag.vector_store import ChromaVectorStore

logger = logging.getLogger(__name__)


class Retriever:
    """Format vector-store hits into an LLM-ready context block."""

    def __init__(self, store: ChromaVectorStore) -> None:
        self.store = store

    def retrieve_context(self, query: str, k: int = 3) -> str:
        """Return a textual context block; empty string if no docs available."""
        if self.store.is_empty():
            logger.warning(
                "RAG store boş; bağlam üretilemedi. "
                "Doküman yüklemesi sonraki fazda yapılacak."
            )
            return ""
        hits = self.store.search(query, k=k)
        if not hits:
            return ""
        formatted: list[str] = []
        for i, hit in enumerate(hits, start=1):
            source = hit.get("metadata", {}).get("source", "(kaynaksız)")
            formatted.append(f"[{i}] {hit['text']}\n— Kaynak: {source}")
        return "\n\n".join(formatted)
