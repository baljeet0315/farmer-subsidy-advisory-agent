"""RAG inspection / verification harness.

Lets you SEE what the retriever stored and how it answers queries, so the RAG
layer can be verified by hand.

Usage:
    python -m eval.inspect_rag            # full report (build + dump + sample queries)
    python -m eval.inspect_rag dump       # just list every stored chunk + metadata
    python -m eval.inspect_rag "your query here"   # run one query, show top passages
"""
from __future__ import annotations

import sys

import chromadb

from src.retriever import COLLECTION, PERSIST_DIR, build_index, retrieve


def dump_index():
    """Print every stored chunk with its scheme_id + source, grouped by scheme."""
    col = chromadb.PersistentClient(path=PERSIST_DIR).get_collection(COLLECTION)
    data = col.get(include=["documents", "metadatas"])
    by_scheme: dict[str, list] = {}
    for doc, meta in zip(data["documents"], data["metadatas"]):
        by_scheme.setdefault(meta["scheme_id"], []).append((meta["chunk"], doc, meta["source_url"]))
    print(f"\n=== STORED INDEX: {len(data['documents'])} chunks across {len(by_scheme)} schemes ===\n")
    for sid in sorted(by_scheme):
        chunks = sorted(by_scheme[sid])
        print(f"● {sid}  ({len(chunks)} chunk(s))  source: {chunks[0][2]}")
        for idx, doc, _ in chunks:
            print(f"    [{idx}] {doc[:110].strip()}...")
        print()


def run_query(q: str, scheme_ids=None, k: int = 3):
    tag = f" (filtered to {scheme_ids})" if scheme_ids else ""
    print(f'\n? QUERY: "{q}"{tag}')
    for r in retrieve(q, scheme_ids=scheme_ids, k=k):
        print(f"    [dist {r['distance']:.3f}] {r['scheme_id']:24} | {r['text'][:75].strip()}...")


def full_report():
    n = build_index()
    print(f"Built index: {n} chunks.")
    dump_index()
    print("=== SAMPLE QUERIES (unfiltered — tests ranking) ===")
    run_query("subsidy for solar water pump")
    run_query("machine to stop burning paddy stubble")
    run_query("free electricity for my tubewell")
    run_query("cash incentive to switch from paddy to maize")
    run_query("crop loss compensation after flood")
    print("\n=== FILTERED QUERIES (tests scheme_id scoping — how the agent actually calls it) ===")
    run_query("what documents do I need and what do I get", scheme_ids=["pm_kisan"])
    run_query("what documents do I need and what do I get", scheme_ids=["pb_crop_diversification"])


if __name__ == "__main__":
    if len(sys.argv) == 1:
        full_report()
    elif sys.argv[1] == "dump":
        dump_index()
    else:
        run_query(" ".join(sys.argv[1:]))
