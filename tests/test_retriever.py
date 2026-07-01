"""Tests for the RAG retriever: chunking, index build, and scheme_id filtering.

These build a real (small) ChromaDB index from data/scheme_docs using the
offline TF-IDF backend, so they need no network or model download.
"""
from __future__ import annotations

import pytest

from src.retriever import build_index, chunk_text, retrieve


def test_chunk_text_overlap():
    words = " ".join(f"w{i}" for i in range(300))
    chunks = chunk_text(words, size=130, overlap=30)
    assert len(chunks) >= 2
    # consecutive chunks should share overlapping words
    first_tail = chunks[0].split()[-30:]
    second_head = chunks[1].split()[:30]
    assert set(first_tail) & set(second_head)


def test_chunk_text_empty():
    assert chunk_text("") == []


@pytest.fixture(scope="module")
def built_index():
    n = build_index()
    assert n > 0
    return n


def test_index_has_chunks(built_index):
    assert built_index >= 8  # at least one chunk per scheme


def test_retrieve_filter_single_scheme(built_index):
    res = retrieve("documents and benefit", scheme_ids=["pb_crop_diversification"], k=3)
    assert res
    assert all(r["scheme_id"] == "pb_crop_diversification" for r in res)


def test_retrieve_filter_candidate_set(built_index):
    res = retrieve("free electricity tubewell loan", scheme_ids=["pb_free_power", "kcc"], k=4)
    assert res
    assert all(r["scheme_id"] in ("pb_free_power", "kcc") for r in res)


def test_retrieve_relevance_unfiltered(built_index):
    # A solar-pump query should rank PM-KUSUM first without any filter.
    res = retrieve("subsidy for solar water pump irrigation", k=3)
    assert res[0]["scheme_id"] == "pm_kusum"
