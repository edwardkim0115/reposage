from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from openai import APIConnectionError, APITimeoutError, InternalServerError, OpenAI, RateLimitError
from pydantic import BaseModel, Field
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from reposage.config import get_settings
from reposage.models import CodeChunk


class GroundedAnswer(BaseModel):
    answer: str
    citation_ids: list[str] = Field(default_factory=list)
    suggested_follow_ups: list[str] = Field(default_factory=list)


def _client() -> OpenAI:
    settings = get_settings()
    if settings.openai_api_key is None:
        raise RuntimeError("OPENAI_API_KEY is required for indexing and chat.")
    return OpenAI(api_key=settings.openai_api_key.get_secret_value())


@retry(
    wait=wait_exponential(min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type((APIConnectionError, APITimeoutError, InternalServerError, RateLimitError)),
    reraise=True,
)
def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    settings = get_settings()
    if not texts:
        return []
    response = _client().embeddings.create(
        model=settings.openai_embedding_model,
        input=[text[:8000] for text in texts],
    )
    return [item.embedding for item in response.data]


@retry(
    wait=wait_exponential(min=1, max=10),
    stop=stop_after_attempt(2),
    retry=retry_if_exception_type((APIConnectionError, APITimeoutError, InternalServerError, RateLimitError)),
    reraise=True,
)
def answer_question(question: str, chunks: Sequence[CodeChunk]) -> GroundedAnswer:
    settings = get_settings()
    if not chunks:
        return GroundedAnswer(
            answer="I could not find enough indexed context in this repository to answer that yet.",
            citation_ids=[],
            suggested_follow_ups=[],
        )

    context_blocks = []
    for chunk in chunks:
        location = chunk.path
        if chunk.start_line and chunk.end_line:
            location = f"{location}:{chunk.start_line}-{chunk.end_line}"
        context_blocks.append(
            "\n".join(
                [
                    f"Chunk ID: {chunk.id}",
                    f"Path: {location}",
                    f"Type: {chunk.chunk_type}",
                    f"Symbol: {chunk.symbol_name or 'n/a'}",
                    "Content:",
                    chunk.content,
                ]
            )
        )

    system_prompt = (
        "You are RepoSage, a repository question-answering assistant. "
        "Answer only from the provided repository context. "
        "If evidence is incomplete, say so clearly. "
        "Keep the answer concise but useful. "
        "For 'where' questions, lead with the location. "
        "Return only chunk ids that directly support the answer."
    )
    user_prompt = (
        f"Question:\n{question}\n\n"
        "Retrieved repository context:\n\n"
        + "\n\n---\n\n".join(context_blocks)
    )
    response = _client().responses.parse(
        model=settings.openai_response_model,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        text_format=GroundedAnswer,
    )
    parsed = getattr(response, "output_parsed", None)
    if isinstance(parsed, GroundedAnswer):
        return parsed

    output_text = getattr(response, "output_text", "")
    return GroundedAnswer(answer=output_text or "I could not generate a grounded answer.", citation_ids=[])


def citation_payload(chunk: CodeChunk) -> dict[str, Any]:
    preview = chunk.content.strip().replace("\n", " ")
    return {
        "chunk_id": str(chunk.id),
        "file_id": str(chunk.repository_file_id),
        "path": chunk.path,
        "chunk_type": chunk.chunk_type,
        "symbol_name": chunk.symbol_name,
        "start_line": chunk.start_line,
        "end_line": chunk.end_line,
        "preview": preview[:240],
    }

