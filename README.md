# RepoSage

RepoSage is a web app for asking questions about a codebase.

You can give it a public GitHub repository URL or upload a ZIP file, and it will index the repository, store searchable chunks, and answer questions with file citations. The goal is to make it easier to explore an unfamiliar codebase and trace answers back to the source.

## What it does

- Ingests a public GitHub repository or uploaded ZIP archive
- Filters unsupported, binary, generated, and oversized files
- Extracts semantic code chunks with Tree-sitter when possible
- Falls back to text chunking for docs and unsupported files
- Stores embeddings and searchable metadata in PostgreSQL with pgvector
- Answers natural-language questions with file-aware citations
- Lets you browse indexed files and preview cited source ranges

## Stack

- **Frontend:** Next.js, TypeScript, Tailwind CSS
- **Backend:** FastAPI, SQLAlchemy, Pydantic
- **Worker:** Redis + RQ
- **Database:** PostgreSQL + pgvector
- **Parsing:** Tree-sitter
- **LLM APIs:** OpenAI embeddings + Responses API

## Project layout

```text
.
├── apps
│   ├── api
│   │   ├── alembic
│   │   └── app
│   └── web
│       └── src
├── packages
│   └── reposage
│       ├── repository
│       ├── services
│       └── worker
├── workers
│   └── indexer
├── tests
├── docker-compose.yml
├── Makefile
├── package.json
└── pyproject.toml