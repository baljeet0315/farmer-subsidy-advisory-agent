"""RAG retriever over the scheme/advisory knowledge base.

Explicit, step-by-step pipeline (no framework hiding the stages):

  BUILD (once, when docs change)
    1. load    — for each scheme in scheme_rules.csv, read its {scheme_id}.txt
                 (or .pdf) from data/scheme_docs/  (scheme-driven, so orphan
                 files are ignored)
    2. chunk   — split each doc into overlapping passages, attach metadata
                 (scheme_id, scheme_name, source_url, chunk index)
    3. embed   — turn each passage into a vector. Default backend is TF-IDF
                 (offline, deterministic, no model download); see EMBEDDING NOTE
                 for the semantic upgrade.
    4. store   — persist vectors + text + metadata in a ChromaDB collection

  QUERY (every farmer request)
    5. embed the query with the same fitted vectoriser
    6. similarity search, FILTERED by scheme_id metadata, returns top-k passages

EMBEDDING NOTE
    We embed explicitly and pass vectors to ChromaDB (rather than using a hidden
    embedding_function) so every step is visible. The default is a TF-IDF
    vectoriser fitted on the corpus — it needs no network/model download and is
    fully reproducible, and because retrieval is scoped by scheme_id the ranking
    quality is more than sufficient. To upgrade to semantic embeddings, replace
    `_fit_embedder` / `_embed` with a sentence-transformers model
    (e.g. "intfloat/multilingual-e5-small") — the rest of the pipeline is
    unchanged.

Run `python -m src.retriever build` to (re)build the index.
"""
from __future__ import annotations

import os
import pickle
import sys

import chromadb

from .utils import get_logger, load_schemes

logger = get_logger("retriever")

DATA_DIR = os.environ.get("DATA_DIR", "data")
DOCS_DIR = os.path.join(DATA_DIR, "scheme_docs")
PERSIST_DIR = os.path.join(DATA_DIR, "chroma")
VECTORISER_PATH = os.path.join(PERSIST_DIR, "tfidf.pkl")
COLLECTION = "punjab_schemes"

CHUNK_WORDS = 130
CHUNK_OVERLAP = 30


# --- step 2: chunking --------------------------------------------------------

def chunk_text(text: str, size: int = CHUNK_WORDS, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping word-windows. Short docs yield 1-2 chunks."""
    words = text.split()
    if not words:
        return []
    chunks, start = [], 0
    step = max(1, size - overlap)
    while start < len(words):
        chunk = " ".join(words[start : start + size])
        if chunk.strip():
            chunks.append(chunk)
        start += step
    return chunks


# --- step 1: loading ---------------------------------------------------------

def _read_doc(path: str) -> str:
    """Read a .txt directly, or extract text from a .pdf (lazy pypdf import)."""
    if path.lower().endswith(".pdf"):
        try:
            from pypdf import PdfReader
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("Install pypdf to index PDF scheme docs: pip install pypdf") from e
        reader = PdfReader(path)
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    with open(path, encoding="utf-8") as f:
        return f.read()


# --- step 3: embedding (TF-IDF backend) --------------------------------------

def _fit_embedder(corpus: list[str]):
    """Fit and persist a TF-IDF vectoriser on the chunk corpus."""
    from sklearn.feature_extraction.text import TfidfVectorizer

    vec = TfidfVectorizer(lowercase=True, stop_words="english", ngram_range=(1, 2))
    vec.fit(corpus)
    os.makedirs(PERSIST_DIR, exist_ok=True)
    with open(VECTORISER_PATH, "wb") as f:
        pickle.dump(vec, f)
    return vec


def _load_embedder():
    with open(VECTORISER_PATH, "rb") as f:
        return pickle.load(f)


def _embed(vec, texts: list[str]) -> list[list[float]]:
    return vec.transform(texts).toarray().astype(float).tolist()


def _client() -> "chromadb.api.ClientAPI":
    return chromadb.PersistentClient(path=PERSIST_DIR)


# --- steps 1-4: build --------------------------------------------------------

def build_index(docs_dir: str = DOCS_DIR, rebuild: bool = True) -> int:
    """Build/refresh the vector index from the scheme docs. Returns chunk count.

    Scheme-driven: iterates schemes from scheme_rules.csv and loads each one's
    document, so stray files in docs_dir are never indexed.
    """
    # 1-2: load + chunk (collect corpus first so the embedder can be fitted)
    entries = []  # (id, text, metadata)
    for scheme in load_schemes():
        path_pdf = os.path.join(docs_dir, f"{scheme.scheme_id}.pdf")
        path_txt = os.path.join(docs_dir, f"{scheme.scheme_id}.txt")
        path = path_pdf if os.path.exists(path_pdf) else path_txt
        if not os.path.exists(path):
            logger.warning("No document found for scheme %s", scheme.scheme_id)
            continue
        for i, chunk in enumerate(chunk_text(_read_doc(path))):
            entries.append((
                f"{scheme.scheme_id}::{i}",
                chunk,
                {"scheme_id": scheme.scheme_id, "scheme_name": scheme.scheme_name,
                 "source_url": scheme.source_url or "", "chunk": i},
            ))

    if not entries:
        logger.warning("No documents indexed.")
        return 0

    ids = [e[0] for e in entries]
    documents = [e[1] for e in entries]
    metadatas = [e[2] for e in entries]

    # 3: embed
    vec = _fit_embedder(documents)
    embeddings = _embed(vec, documents)

    # 4: store
    client = _client()
    if rebuild:
        try:
            client.delete_collection(COLLECTION)
        except Exception:
            pass
    collection = client.get_or_create_collection(
        name=COLLECTION, metadata={"hnsw:space": "cosine"}
    )
    collection.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)
    logger.info("Indexed %d chunks into '%s'", len(documents), COLLECTION)
    return len(documents)


# --- steps 5-6: query --------------------------------------------------------

def retrieve(query: str, scheme_ids: list[str] | None = None, k: int = 4) -> list[dict]:
    """Return top-k passages, optionally restricted to specific scheme_ids.

    Each result: {text, scheme_id, scheme_name, source_url, distance}.
    """
    vec = _load_embedder()
    q_emb = _embed(vec, [query])
    collection = _client().get_collection(COLLECTION)
    where = None
    if scheme_ids:
        where = {"scheme_id": scheme_ids[0]} if len(scheme_ids) == 1 else {"scheme_id": {"$in": scheme_ids}}
    res = collection.query(query_embeddings=q_emb, n_results=k, where=where)
    out = []
    for text, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        out.append({
            "text": text,
            "scheme_id": meta.get("scheme_id"),
            "scheme_name": meta.get("scheme_name"),
            "source_url": meta.get("source_url"),
            "distance": dist,
        })
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "build":
        n = build_index()
        print(f"Built index: {n} chunks -> {PERSIST_DIR}/{COLLECTION}")
    elif cmd == "query":
        q = sys.argv[2] if len(sys.argv) > 2 else "documents needed for solar pump subsidy"
        for r in retrieve(q, k=3):
            print(f"[{r['distance']:.3f}] {r['scheme_id']}: {r['text'][:90]}...")
