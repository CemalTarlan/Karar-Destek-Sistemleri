"""Chroma vector store wrapper — empty by design.

The actual document corpus will be ingested in a later phase (TR Sağlık
Bakanlığı tebliğleri, ESI/MTS reference material). For now this class
exposes a stable interface so the rest of the system can be wired up
without importing chromadb at hot-path call sites.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ChromaVectorStore:
    """Lazy wrapper around a chromadb persistent client + collection."""

    def __init__(
        self,
        persist_dir: Path,
        collection_name: str = "medsim_triage",
    ) -> None:
        self.persist_dir = Path(persist_dir)
        self.collection_name = collection_name
        self._client: Any | None = None
        self._collection: Any | None = None

    def _ensure_collection(self) -> Any:
        if self._collection is not None:
            return self._collection
        try:
            import chromadb
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "chromadb yüklü değil. `pip install -e .[dev]` ile kurun."
            ) from exc

        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(self.persist_dir))
        self._collection = self._client.get_or_create_collection(self.collection_name)
        logger.info(
            "Chroma collection '%s' ready at %s",
            self.collection_name,
            self.persist_dir,
        )
        return self._collection

    def add_documents(self, docs: list[dict[str, Any]]) -> None:
        """Add documents to the collection.

        Each `dict` must have keys: `id`, `text`, optional `metadata`.

        # TODO: doküman yüklemesi sonraki fazda — Sağlık Bakanlığı tebliğleri,
        # ESI v4 referansı ve dahili kural notları burada indekslenecek.
        """
        if not docs:
            logger.info("add_documents called with no documents; no-op.")
            return
        collection = self._ensure_collection()
        ids = [str(d["id"]) for d in docs]
        texts = [str(d["text"]) for d in docs]
        metadatas = [dict(d.get("metadata", {})) for d in docs]
        collection.add(ids=ids, documents=texts, metadatas=metadatas)
        logger.info("Indexed %d documents into '%s'", len(ids), self.collection_name)

    def search(self, query: str, k: int = 3) -> list[dict[str, Any]]:
        """Return up to `k` nearest documents to `query`."""
        if not query.strip():
            return []
        collection = self._ensure_collection()
        if collection.count() == 0:
            logger.warning(
                "Vector store '%s' is empty; returning no results. "
                "Doküman yüklemesi henüz yapılmadı (sonraki fazda).",
                self.collection_name,
            )
            return []
        result = collection.query(query_texts=[query], n_results=k)
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0] or [{} for _ in documents]
        ids = result.get("ids", [[]])[0]
        return [
            {"id": ids[i], "text": documents[i], "metadata": metadatas[i]}
            for i in range(len(documents))
        ]

    def is_empty(self) -> bool:
        try:
            collection = self._ensure_collection()
            return bool(collection.count() == 0)
        except Exception as exc:  # pragma: no cover
            logger.warning("Could not inspect Chroma collection: %s", exc)
            return True
