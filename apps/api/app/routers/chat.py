from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.app.deps import get_db
from reposage.models import ChatSession
from reposage.schemas import ChatMessageCreate, ChatMessageRead, ChatReply, ChatSessionCreate, ChatSessionRead
from reposage.services.chat import create_chat_session, list_messages, post_chat_message
from reposage.services.projects import get_project, list_chat_sessions

router = APIRouter(tags=["chat"])


@router.post("/projects/{project_id}/chat/sessions", response_model=ChatSessionRead, status_code=status.HTTP_201_CREATED)
def create_chat_session_endpoint(
    project_id: str,
    payload: ChatSessionCreate,
    db: Session = Depends(get_db),
) -> ChatSessionRead:
    if get_project(db, project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    return ChatSessionRead.model_validate(create_chat_session(db, project_id, payload.title))


@router.get("/projects/{project_id}/chat/sessions", response_model=list[ChatSessionRead])
def list_chat_sessions_endpoint(project_id: str, db: Session = Depends(get_db)) -> list[ChatSessionRead]:
    if get_project(db, project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    return [ChatSessionRead.model_validate(session_obj) for session_obj in list_chat_sessions(db, project_id)]


@router.get("/chat/sessions/{chat_session_id}/messages", response_model=list[ChatMessageRead])
def list_messages_endpoint(chat_session_id: str, db: Session = Depends(get_db)) -> list[ChatMessageRead]:
    if db.get(ChatSession, chat_session_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found.")
    return [ChatMessageRead.model_validate(message) for message in list_messages(db, chat_session_id)]


@router.post("/chat/sessions/{chat_session_id}/messages", response_model=ChatReply, status_code=status.HTTP_201_CREATED)
def create_message_endpoint(
    chat_session_id: str,
    payload: ChatMessageCreate,
    db: Session = Depends(get_db),
) -> ChatReply:
    try:
        session_obj, user_message, assistant_message, follow_ups = post_chat_message(
            db, chat_session_id, payload.content
        )
    except ValueError as exc:
        message = str(exc)
        status_code = (
            status.HTTP_404_NOT_FOUND
            if message in {"Chat session not found.", "Project not found."}
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=message) from exc
    return ChatReply(
        session=ChatSessionRead.model_validate(session_obj),
        user_message=ChatMessageRead.model_validate(user_message),
        assistant_message=ChatMessageRead.model_validate(assistant_message),
        suggested_follow_ups=follow_ups,
    )
