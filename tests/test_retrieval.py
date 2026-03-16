from __future__ import annotations

from types import SimpleNamespace

from reposage.services.retrieval import RankedChunk, classify_query, merge_ranked_results


def _chunk(chunk_id: str, *, path: str, chunk_type: str, symbol_name: str | None = None):
    return SimpleNamespace(
        id=chunk_id,
        path=path,
        chunk_type=chunk_type,
        symbol_name=symbol_name,
    )


def test_query_classification() -> None:
    assert classify_query("Where is authentication handled?") == "where"
    assert classify_query("How does signup work?") == "how"
    assert classify_query("What does AuthService do?") == "symbol"


def test_merge_ranked_results_boosts_symbol_and_path_matches() -> None:
    auth_chunk = _chunk("1", path="app/auth/service.py", chunk_type="class", symbol_name="AuthService")
    docs_chunk = _chunk("2", path="docs/authentication.md", chunk_type="doc_section")

    lexical = [
        RankedChunk(chunk=auth_chunk, lexical_score=0.8, path_score=0.7, symbol_score=0.9),
        RankedChunk(chunk=docs_chunk, lexical_score=0.9, path_score=0.3, symbol_score=0.0),
    ]
    vector = [
        RankedChunk(chunk=auth_chunk, vector_score=0.65),
        RankedChunk(chunk=docs_chunk, vector_score=0.7),
    ]

    merged = merge_ranked_results(lexical, vector, query="What does AuthService do?", limit=2)

    assert merged[0].chunk.id == "1"
    assert merged[0].final_score >= merged[1].final_score

