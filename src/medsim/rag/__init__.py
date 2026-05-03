"""RAG skeleton (vector store + retriever).

Documents are intentionally NOT loaded yet — see `add_documents`.
"""

from medsim.rag.retriever import Retriever
from medsim.rag.vector_store import ChromaVectorStore

__all__ = ["ChromaVectorStore", "Retriever"]
