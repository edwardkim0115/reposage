from __future__ import annotations

from datetime import datetime, timedelta

from reposage.enums import ProjectStatus, SourceType
from reposage.models import ChatSession, CodeChunk, Project, RepositoryFile
from reposage.services.llm import GroundedAnswer


def test_create_project_and_list_projects(client) -> None:
    create_response = client.post("/projects", json={"name": "Repo audit"})
    assert create_response.status_code == 201
    assert create_response.json()["name"] == "Repo audit"

    list_response = client.get("/projects")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_create_project_rejects_blank_name(client) -> None:
    response = client.post("/projects", json={"name": "   "})
    assert response.status_code == 422


def test_create_github_project_enqueues_job(client, monkeypatch) -> None:
    enqueued: list[str] = []
    monkeypatch.setattr("apps.api.app.routers.projects.enqueue_index_job", lambda job_id: enqueued.append(job_id))

    response = client.post(
        "/projects/github",
        json={"name": "FastAPI repo", "source_url": "https://github.com/tiangolo/fastapi"},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "queued"
    assert len(enqueued) == 1


def test_file_detail_and_chunks_endpoint(client, db_session) -> None:
    project = Project(name="Indexed repo", source_type=SourceType.ZIP, status=ProjectStatus.READY)
    db_session.add(project)
    db_session.flush()
    repo_file = RepositoryFile(
        project_id=project.id,
        path="src/auth.py",
        language="python",
        file_size=120,
        checksum="abc",
        is_supported=True,
        content_text="def login():\n    return True",
        summary="python file; contains function chunks",
    )
    db_session.add(repo_file)
    db_session.flush()
    chunk = CodeChunk(
        project_id=project.id,
        repository_file_id=repo_file.id,
        path=repo_file.path,
        language="python",
        chunk_index=0,
        chunk_type="function",
        symbol_name="login",
        start_line=1,
        end_line=2,
        content="def login():\n    return True",
        search_text="src/auth.py login def login return true",
        chunk_metadata={},
    )
    db_session.add(chunk)
    db_session.commit()

    file_response = client.get(f"/projects/{project.id}/files/{repo_file.id}")
    assert file_response.status_code == 200
    assert file_response.json()["path"] == "src/auth.py"
    assert len(file_response.json()["chunks"]) == 1

    chunks_response = client.get(f"/projects/{project.id}/chunks")
    assert chunks_response.status_code == 200
    assert chunks_response.json()[0]["symbol_name"] == "login"


def test_chat_happy_path_returns_grounded_citations(client, db_session, monkeypatch) -> None:
    project = Project(name="Chat repo", source_type=SourceType.ZIP, status=ProjectStatus.READY)
    db_session.add(project)
    db_session.flush()
    repo_file = RepositoryFile(
        project_id=project.id,
        path="src/api.py",
        language="python",
        file_size=120,
        checksum="def",
        is_supported=True,
        content_text="def signup():\n    return create_user()",
        summary="python file; contains function chunks",
    )
    db_session.add(repo_file)
    db_session.flush()
    chunk = CodeChunk(
        project_id=project.id,
        repository_file_id=repo_file.id,
        path=repo_file.path,
        language="python",
        chunk_index=0,
        chunk_type="function",
        symbol_name="signup",
        start_line=1,
        end_line=2,
        content="def signup():\n    return create_user()",
        search_text="src/api.py signup def signup create_user",
        chunk_metadata={},
    )
    chat_session = ChatSession(project_id=project.id, title="Signup flow")
    db_session.add_all([chunk, chat_session])
    db_session.commit()
    previous_updated_at = chat_session.updated_at

    monkeypatch.setattr("reposage.services.chat.retrieve_relevant_chunks", lambda *args, **kwargs: [chunk])
    monkeypatch.setattr(
        "reposage.services.chat.answer_question",
        lambda *_args, **_kwargs: GroundedAnswer(
            answer="Signup is implemented in `src/api.py`.",
            citation_ids=[str(chunk.id)],
            suggested_follow_ups=["What calls signup?"],
        ),
    )

    response = client.post(
        f"/chat/sessions/{chat_session.id}/messages",
        json={"content": "How does signup work?"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["assistant_message"]["citations"][0]["path"] == "src/api.py"
    assert payload["suggested_follow_ups"] == ["What calls signup?"]
    db_session.refresh(chat_session)
    assert chat_session.updated_at >= previous_updated_at


def test_chat_updates_session_timestamp(client, db_session, monkeypatch) -> None:
    project = Project(name="Chat repo", source_type=SourceType.ZIP, status=ProjectStatus.READY)
    db_session.add(project)
    db_session.flush()
    created_at = datetime.utcnow() - timedelta(days=1)
    chat_session = ChatSession(
        project_id=project.id,
        title="Old session",
        created_at=created_at,
        updated_at=created_at,
    )
    db_session.add(chat_session)
    db_session.commit()

    monkeypatch.setattr("reposage.services.chat.retrieve_relevant_chunks", lambda *args, **kwargs: [])

    response = client.post(
        f"/chat/sessions/{chat_session.id}/messages",
        json={"content": "Where is auth handled?"},
    )

    assert response.status_code == 201
    db_session.refresh(chat_session)
    assert chat_session.updated_at > created_at


def test_chat_rejects_blank_message_content(client, db_session) -> None:
    project = Project(name="Chat repo", source_type=SourceType.ZIP, status=ProjectStatus.READY)
    db_session.add(project)
    db_session.flush()
    chat_session = ChatSession(project_id=project.id, title="Empty")
    db_session.add(chat_session)
    db_session.commit()

    response = client.post(
        f"/chat/sessions/{chat_session.id}/messages",
        json={"content": "   "},
    )

    assert response.status_code == 422
