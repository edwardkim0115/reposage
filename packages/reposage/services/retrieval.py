from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
import re
from typing import Iterable

from sqlalchemy import case, desc, func, literal, or_, select
from sqlalchemy.orm import Session

from reposage.models import CodeChunk
from reposage.services.llm import embed_texts


@dataclass(slots=True)
class RankedChunk:
    chunk: CodeChunk
    lexical_score: float = 0.0
    vector_score: float = 0.0
    path_score: float = 0.0
    symbol_score: float = 0.0
    final_score: float = 0.0


QUERY_STOPWORDS = {
    "a",
    "an",
    "and",
    "code",
    "do",
    "does",
    "for",
    "function",
    "handle",
    "handled",
    "how",
    "implementation",
    "implemented",
    "in",
    "is",
    "method",
    "of",
    "route",
    "the",
    "this",
    "what",
    "where",
    "which",
    "work",
    "works",
}
QUERY_TERM_RE = re.compile(r"[A-Za-z0-9_./-]+")


def classify_query(query: str) -> str:
    lowered = query.lower()
    if lowered.startswith("where") or "where is" in lowered or "which file" in lowered:
        return "where"
    if lowered.startswith("how") or "how does" in lowered:
        return "how"
    if (
        "class" in lowered
        or "function" in lowered
        or "method" in lowered
        or lowered.startswith("what does")
        or lowered.startswith("what is")
    ):
        return "symbol"
    return "general"


def extract_query_terms(query: str) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for raw_term in QUERY_TERM_RE.findall(query.lower()):
        term = raw_term.strip("._-/")
        if not term or term in QUERY_STOPWORDS or len(term) <= 1:
            continue
        if term in seen:
            continue
        seen.add(term)
        terms.append(term)
    return terms


def score_text_matches(text: str | None, query_terms: list[str]) -> float:
    if not text or not query_terms:
        return 0.0
    lowered = text.lower()
    matches = sum(1 for term in query_terms if term in lowered)
    return matches / len(query_terms)


def merge_ranked_results(
    lexical_results: Iterable[RankedChunk],
    vector_results: Iterable[RankedChunk],
    *,
    query: str,
    limit: int,
) -> list[RankedChunk]:
    query_type = classify_query(query)
    weight_map = {
        "general": {"lexical": 0.45, "vector": 0.4, "path": 0.05, "symbol": 0.1},
        "where": {"lexical": 0.45, "vector": 0.2, "path": 0.2, "symbol": 0.15},
        "how": {"lexical": 0.35, "vector": 0.5, "path": 0.05, "symbol": 0.1},
        "symbol": {"lexical": 0.35, "vector": 0.25, "path": 0.1, "symbol": 0.3},
    }
    weights = weight_map[query_type]

    merged: dict[str, RankedChunk] = {}
    for result in list(lexical_results) + list(vector_results):
        key = str(result.chunk.id)
        current = merged.get(key)
        if current is None:
            merged[key] = RankedChunk(
                chunk=result.chunk,
                lexical_score=result.lexical_score,
                vector_score=result.vector_score,
                path_score=result.path_score,
                symbol_score=result.symbol_score,
            )
            continue
        current.lexical_score = max(current.lexical_score, result.lexical_score)
        current.vector_score = max(current.vector_score, result.vector_score)
        current.path_score = max(current.path_score, result.path_score)
        current.symbol_score = max(current.symbol_score, result.symbol_score)

    lexical_max = max((item.lexical_score for item in merged.values()), default=0.0) or 1.0
    vector_max = max((item.vector_score for item in merged.values()), default=0.0) or 1.0

    for item in merged.values():
        lexical = item.lexical_score / lexical_max
        vector = item.vector_score / vector_max
        path = max(0.0, min(item.path_score, 1.0))
        symbol = max(0.0, min(item.symbol_score, 1.0))
        code_bias = 0.05 if item.chunk.chunk_type not in {"doc_section", "fallback_text"} else 0.0
        item.final_score = (
            weights["lexical"] * lexical
            + weights["vector"] * vector
            + weights["path"] * path
            + weights["symbol"] * symbol
            + code_bias
        )

    return sorted(merged.values(), key=lambda item: item.final_score, reverse=True)[:limit]


def retrieve_relevant_chunks(session: Session, project_id: str, query: str, *, limit: int = 8) -> list[CodeChunk]:
    lexical_results = retrieve_lexical_chunks(session, project_id, query, limit=limit * 3)
    vector_results: list[RankedChunk] = []
    if session.bind and session.bind.dialect.name != "sqlite":
        try:
            vector_results = retrieve_vector_chunks(session, project_id, query, limit=limit * 3)
        except RuntimeError:
            vector_results = []
    merged = merge_ranked_results(lexical_results, vector_results, query=query, limit=limit)
    return [item.chunk for item in merged]


def retrieve_lexical_chunks(session: Session, project_id: str, query: str, *, limit: int) -> list[RankedChunk]:
    if session.bind and session.bind.dialect.name == "sqlite":
        return _retrieve_lexical_chunks_sqlite(session, project_id, query, limit)

    query_terms = extract_query_terms(query)
    ts_query = func.websearch_to_tsquery("english", query)

    path_score = literal(0.0)
    symbol_score = literal(0.0)
    extra_predicates = []

    if query_terms:
        path_predicates = [func.lower(CodeChunk.path).like(f"%{term}%") for term in query_terms]
        symbol_predicates = [
            func.lower(func.coalesce(CodeChunk.symbol_name, "")).like(f"%{term}%") for term in query_terms
        ]
        extra_predicates.extend([or_(*path_predicates), or_(*symbol_predicates)])

        path_score = sum(
            (case((predicate, 1.0), else_=0.0) for predicate in path_predicates),
            start=literal(0.0),
        ) / float(len(query_terms))
        symbol_score = sum(
            (case((predicate, 1.0), else_=0.0) for predicate in symbol_predicates),
            start=literal(0.0),
        ) / float(len(query_terms))

    statement = (
        select(
            CodeChunk,
            func.ts_rank_cd(func.to_tsvector("english", CodeChunk.search_text), ts_query).label("lexical_score"),
            path_score.label("path_score"),
            symbol_score.label("symbol_score"),
        )
        .where(
            CodeChunk.project_id == project_id,
            or_(
                func.to_tsvector("english", CodeChunk.search_text).op("@@")(ts_query),
                *extra_predicates,
            ),
        )
        .order_by(desc("lexical_score"), desc("symbol_score"), desc("path_score"))
        .limit(limit)
    )

    rows = session.execute(statement).all()
    return [
        RankedChunk(
            chunk=row[0],
            lexical_score=float(row.lexical_score or 0.0),
            path_score=float(row.path_score or 0.0),
            symbol_score=float(row.symbol_score or 0.0),
        )
        for row in rows
    ]


def _retrieve_lexical_chunks_sqlite(session: Session, project_id: str, query: str, limit: int) -> list[RankedChunk]:
    query_terms = extract_query_terms(query)
    lexical_terms = query_terms or [term for term in query.lower().split() if term]
    chunks = session.scalars(select(CodeChunk).where(CodeChunk.project_id == project_id)).all()
    results: list[RankedChunk] = []
    for chunk in chunks:
        haystack = f"{chunk.path} {chunk.symbol_name or ''} {chunk.search_text}".lower()
        lexical_score = sum(haystack.count(term) for term in lexical_terms)
        if lexical_score == 0:
            continue
        path_score = score_text_matches(chunk.path, query_terms)
        symbol_score = score_text_matches(chunk.symbol_name, query_terms)
        results.append(
            RankedChunk(
                chunk=chunk,
                lexical_score=float(lexical_score),
                path_score=path_score,
                symbol_score=symbol_score,
            )
        )
    return sorted(results, key=lambda item: item.lexical_score, reverse=True)[:limit]


def retrieve_vector_chunks(session: Session, project_id: str, query: str, *, limit: int) -> list[RankedChunk]:
    query_embedding = embed_texts([query])[0]
    statement = (
        select(
            CodeChunk,
            (1 - CodeChunk.embedding.cosine_distance(query_embedding)).label("vector_score"),
        )
        .where(CodeChunk.project_id == project_id, CodeChunk.embedding.is_not(None))
        .order_by(desc("vector_score"))
        .limit(limit)
    )
    rows = session.execute(statement).all()
    return [RankedChunk(chunk=row[0], vector_score=float(row.vector_score or 0.0)) for row in rows]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)
