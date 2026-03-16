from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_archive_path", sa.String(length=1024), nullable=True),
        sa.Column("default_branch", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("last_indexed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_projects_status", "projects", ["status"])
    op.create_index("ix_projects_updated_at", "projects", ["updated_at"])

    op.create_table(
        "repository_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("path", sa.String(length=1024), nullable=False),
        sa.Column("language", sa.String(length=64), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("is_supported", sa.Boolean(), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.UniqueConstraint("project_id", "path", name="uq_repository_files_project_path"),
    )
    op.create_index("ix_repository_files_project_id", "repository_files", ["project_id"])
    op.create_index("ix_repository_files_path", "repository_files", ["path"])

    op.create_table(
        "code_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("repository_file_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("repository_files.id", ondelete="CASCADE"), nullable=False),
        sa.Column("path", sa.String(length=1024), nullable=False),
        sa.Column("language", sa.String(length=64), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_type", sa.String(length=64), nullable=False),
        sa.Column("symbol_name", sa.String(length=255), nullable=True),
        sa.Column("start_line", sa.Integer(), nullable=True),
        sa.Column("end_line", sa.Integer(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("search_text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.UniqueConstraint("repository_file_id", "chunk_index", name="uq_code_chunks_file_chunk"),
    )
    op.create_index("ix_code_chunks_project_id", "code_chunks", ["project_id"])
    op.create_index("ix_code_chunks_repository_file_id", "code_chunks", ["repository_file_id"])
    op.create_index("ix_code_chunks_path", "code_chunks", ["path"])
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_code_chunks_search_text_gin "
        "ON code_chunks USING GIN (to_tsvector('english', search_text))"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_code_chunks_path_trgm "
        "ON code_chunks USING GIN (path gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_code_chunks_symbol_trgm "
        "ON code_chunks USING GIN (symbol_name gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_code_chunks_embedding_hnsw "
        "ON code_chunks USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_table(
        "chat_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_chat_sessions_project_id", "chat_sessions", ["project_id"])

    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("chat_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_chat_messages_chat_session_id", "chat_messages", ["chat_session_id"])

    op.create_table(
        "index_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_index_jobs_project_id", "index_jobs", ["project_id"])
    op.create_index("ix_index_jobs_status", "index_jobs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_index_jobs_status", table_name="index_jobs")
    op.drop_index("ix_index_jobs_project_id", table_name="index_jobs")
    op.drop_table("index_jobs")

    op.drop_index("ix_chat_messages_chat_session_id", table_name="chat_messages")
    op.drop_table("chat_messages")

    op.drop_index("ix_chat_sessions_project_id", table_name="chat_sessions")
    op.drop_table("chat_sessions")

    op.execute("DROP INDEX IF EXISTS ix_code_chunks_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_code_chunks_symbol_trgm")
    op.execute("DROP INDEX IF EXISTS ix_code_chunks_path_trgm")
    op.execute("DROP INDEX IF EXISTS ix_code_chunks_search_text_gin")
    op.drop_index("ix_code_chunks_path", table_name="code_chunks")
    op.drop_index("ix_code_chunks_repository_file_id", table_name="code_chunks")
    op.drop_index("ix_code_chunks_project_id", table_name="code_chunks")
    op.drop_table("code_chunks")

    op.drop_index("ix_repository_files_path", table_name="repository_files")
    op.drop_index("ix_repository_files_project_id", table_name="repository_files")
    op.drop_table("repository_files")

    op.drop_index("ix_projects_updated_at", table_name="projects")
    op.drop_index("ix_projects_status", table_name="projects")
    op.drop_table("projects")

