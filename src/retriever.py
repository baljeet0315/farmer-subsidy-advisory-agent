"""RAG retriever over the scheme/advisory document knowledge base.

Builds a vector index (ChromaDB + sentence-transformers) from data/scheme_docs/
and retrieves the passages relevant to a candidate scheme set, so the LLMs
explain grounded in real text rather than inventing scheme details.

TODO (Day 4):
- build_index(docs_dir) -> persists vector store
- retrieve(query, scheme_ids, k) -> list[passage]
"""
from __future__ import annotations


def build_index(docs_dir: str) -> None:
    """Embed and persist the scheme docs. TODO: implement."""
    raise NotImplementedError


def retrieve(query: str, scheme_ids: list[str], k: int = 4) -> list[str]:
    """Return top-k grounded passages for the candidate schemes. TODO: implement."""
    raise NotImplementedError
