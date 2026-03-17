from __future__ import annotations

from datetime import datetime
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from reposage.enums import MessageRole, ProjectStatus
from reposage.models import ChatMessage, ChatSession, Project
from reposage.services.llm import answer_question, citation_payload
from reposage.services.retrieval import retrieve_relevant_chunks

logger = logging.getLogger(__name__)


def create_chat_session(session: Session, project_id: str, title: str | None = None) -> ChatSession:
    normalized_title = title.strip() if title else None
    chat_session = ChatSession(project_id=project_id, title=normalized_title or None)
    session.add(chat_session)
    session.commit()
    session.refresh(chat_session)
    return chat_session


def list_messages(session: Session, chat_session_id: str) -> list[ChatMessage]:
    statement = (
        select(ChatMessage)
        .where(ChatMessage.chat_session_id == chat_session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    return list(session.scalars(statement).all())


def build_grounded_fallback_answer(chunks: list[CodeChunk], *, limit: int = 3) -> str:
    if not chunks:
        return "I could not find relevant indexed code or docs for that question."

    lines = ["I couldn't use the language model, but these indexed locations look most relevant:"]
    for chunk in chunks[:limit]:
        location = chunk.path
        if chunk.start_line and chunk.end_line:
            location = f"{location}:{chunk.start_line}-{chunk.end_line}"
        label = chunk.symbol_name or chunk.chunk_type
        lines.append(f"- {location} ({label})")
    return "\n".join(lines)


def post_chat_message(session: Session, chat_session_id: str, content: str) -> tuple[ChatSession, ChatMessage, ChatMessage, list[str]]:
    chat_session = session.get(ChatSession, chat_session_id)
    if chat_session is None:
        raise ValueError("Chat session not found.")

    project = session.get(Project, chat_session.project_id)
    if project is None:
        raise ValueError("Project not found.")

    content = content.strip()
    if not content:
        raise ValueError("Message content cannot be blank.")

    user_message = ChatMessage(chat_session_id=chat_session.id, role=MessageRole.USER, content=content)
    session.add(user_message)
    session.flush()

    follow_ups: list[str] = []
    citations: list[dict] = []
    if project.status != ProjectStatus.READY:
        answer_text = "This project is not indexed yet. Wait for indexing to finish, then ask again."
    else:
        retrieved_chunks = retrieve_relevant_chunks(session, str(project.id), content)
        if not retrieved_chunks:
            answer_text = "I could not find relevant indexed code or docs for that question."
        else:
            try:
                answer = answer_question(content, retrieved_chunks)
                answer_text = answer.answer
                cited_ids = (
                    set(answer.citation_ids)
                    if answer.citation_ids
                    else {str(chunk.id) for chunk in retrieved_chunks[:3]}
                )
                follow_ups = answer.suggested_follow_ups[:3]
            except Exception as exc:
                logger.warning("Answer generation failed; returning retrieval-only fallback: %s", exc)
                answer_text = build_grounded_fallback_answer(retrieved_chunks)
                cited_ids = {str(chunk.id) for chunk in retrieved_chunks[:3]}
            citations = [citation_payload(chunk) for chunk in retrieved_chunks if str(chunk.id) in cited_ids]
            if not citations:
                citations = [citation_payload(chunk) for chunk in retrieved_chunks[:3]]

    assistant_message = ChatMessage(
        chat_session_id=chat_session.id,
        role=MessageRole.ASSISTANT,
        content=answer_text,
        citations=citations or None,
    )
    session.add(assistant_message)
    chat_session.updated_at = datetime.utcnow()
    if chat_session.title is None:
        chat_session.title = content.strip()[:80]
    session.commit()
    session.refresh(chat_session)
    session.refresh(user_message)
    session.refresh(assistant_message)
    return chat_session, user_message, assistant_message, follow_ups
